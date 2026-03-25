# daily_signal_generator.py
# Improved multi-asset daily signal generator
# Designed to run once per day near market close

import yfinance as yf
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import warnings

warnings.filterwarnings("ignore")


class DailySignalGenerator:
    def __init__(self, model_path="ultimate_trading_models.pkl"):
        self.models = {}
        self.scalers = {}
        self.feature_cols = None
        self.model_path = model_path
        self.model_metrics = {}

    def load_or_train_models(self, symbols):
        """Load existing models or train from scratch if invalid."""
        try:
            with open(self.model_path, "rb") as f:
                data = pickle.load(f)

            self.models = data.get("models", {})
            self.scalers = data.get("scalers", {})
            self.feature_cols = data.get("feature_cols", None)
            self.model_metrics = data.get("model_metrics", {})

            valid_symbols = [
                s for s in symbols
                if s in self.models and s in self.scalers
            ]

            if (
                not isinstance(self.models, dict)
                or not isinstance(self.scalers, dict)
                or not isinstance(self.feature_cols, list)
                or len(self.feature_cols) == 0
                or len(valid_symbols) == 0
            ):
                print("⚠ Existing model file is empty or invalid. Retraining...")
                self.models = {}
                self.scalers = {}
                self.feature_cols = None
                self.model_metrics = {}
                self.train_all_models(symbols)
            else:
                print(f"✓ Loaded existing models for {len(valid_symbols)} symbols")

        except Exception as e:
            print(f"⚠ Could not load models: {e}")
            print("Training new models...")
            self.train_all_models(symbols)

    def save_models(self):
        with open(self.model_path, "wb") as f:
            pickle.dump(
                {
                    "models": self.models,
                    "scalers": self.scalers,
                    "feature_cols": self.feature_cols,
                    "model_metrics": self.model_metrics,
                },
                f,
            )

    def get_data(self, symbol, period_days=730):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        data = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if data is None or data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required_cols if c not in data.columns]
        if missing:
            raise ValueError(f"Missing columns for {symbol}: {missing}")

        data = data[required_cols].copy()
        data = data.dropna()

        return data

    def create_features(self, data):
        df = data.copy()

        # Returns
        df["returns_1d"] = df["Close"].pct_change() * 100
        df["returns_3d"] = df["Close"].pct_change(3) * 100
        df["returns_5d"] = df["Close"].pct_change(5) * 100
        df["returns_10d"] = df["Close"].pct_change(10) * 100
        df["returns_20d"] = df["Close"].pct_change(20) * 100

        # Candle structure
        df["high_low_ratio"] = (df["High"] - df["Low"]) / df["Close"] * 100
        df["close_open_ratio"] = (df["Close"] - df["Open"]) / df["Close"] * 100
        df["price_range"] = (df["High"] - df["Low"]) / df["Close"]

        # Moving averages
        for period in [5, 10, 20, 50, 100, 200]:
            df[f"sma{period}"] = df["Close"].rolling(period).mean()
            df[f"close_above_sma{period}"] = (df["Close"] > df[f"sma{period}"]).astype(int)

        df["sma_slope_10"] = df["sma10"].diff()
        df["sma_slope_20"] = df["sma20"].diff()
        df["sma_slope_50"] = df["sma50"].diff()

        # Volatility
        df["volatility_5"] = df["returns_1d"].rolling(5).std()
        df["volatility_10"] = df["returns_1d"].rolling(10).std()
        df["volatility_20"] = df["returns_1d"].rolling(20).std()

        # ATR approximation
        df["atr"] = (df["High"] - df["Low"]).rolling(14).mean()
        df["atr_percent"] = df["atr"] / df["Close"] * 100

        # Momentum / ROC
        df["roc_5"] = (df["Close"] - df["Close"].shift(5)) / df["Close"].shift(5) * 100
        df["roc_10"] = (df["Close"] - df["Close"].shift(10)) / df["Close"].shift(10) * 100
        df["roc_20"] = (df["Close"] - df["Close"].shift(20)) / df["Close"].shift(20) * 100

        df["momentum_5"] = df["Close"].diff(5)
        df["momentum_10"] = df["Close"].diff(10)
        df["momentum_20"] = df["Close"].diff(20)

        # RSI
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # Volume
        df["volume_ma_10"] = df["Volume"].rolling(10).mean()
        df["volume_ma_20"] = df["Volume"].rolling(20).mean()
        df["volume_ratio_10"] = df["Volume"] / df["volume_ma_10"]
        df["volume_ratio_20"] = df["Volume"] / df["volume_ma_20"]

        # Structure
        df["higher_high"] = (df["High"] > df["High"].shift(1)).astype(int)
        df["higher_low"] = (df["Low"] > df["Low"].shift(1)).astype(int)
        df["lower_high"] = (df["High"] < df["High"].shift(1)).astype(int)
        df["lower_low"] = (df["Low"] < df["Low"].shift(1)).astype(int)

        # Distance from mean
        df["distance_from_sma20"] = (df["Close"] - df["sma20"]) / df["sma20"] * 100
        df["distance_from_sma50"] = (df["Close"] - df["sma50"]) / df["sma50"] * 100
        df["zscore_20"] = (df["Close"] - df["sma20"]) / df["volatility_20"].replace(0, np.nan)

        # Trend alignment
        df["sma20_above_sma50"] = (df["sma20"] > df["sma50"]).astype(int)
        df["sma50_above_sma200"] = (df["sma50"] > df["sma200"]).astype(int)

        # Target: next day direction
        df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna()

        return df

    def train_all_models(self, symbols):
        trained_count = 0

        for symbol in symbols:
            try:
                data = self.get_data(symbol, period_days=730)

                if data.empty or len(data) < 260:
                    print(f"Skipping {symbol}: not enough history ({len(data)} rows)")
                    continue

                df = self.create_features(data)

                if df.empty or len(df) < 120:
                    print(f"Skipping {symbol}: not enough usable feature rows")
                    continue

                feature_cols = [
                    c for c in df.columns
                    if c not in ["Open", "High", "Low", "Close", "Volume", "target"]
                ]
                self.feature_cols = feature_cols

                X = df[feature_cols].values
                y = df["target"].values

                if len(np.unique(y)) < 2:
                    print(f"Skipping {symbol}: target has only one class")
                    continue

                split_idx = int(len(X) * 0.8)
                X_train, X_test = X[:split_idx], X[split_idx:]
                y_train, y_test = y[:split_idx], y[split_idx:]

                if len(X_train) < 50 or len(X_test) < 20:
                    print(f"Skipping {symbol}: insufficient split sizes")
                    continue

                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)

                model = RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1,
                    class_weight="balanced_subsample"
                )
                model.fit(X_train_scaled, y_train)

                train_pred = model.predict(X_train_scaled)
                test_pred = model.predict(X_test_scaled)

                train_acc = accuracy_score(y_train, train_pred)
                test_acc = accuracy_score(y_test, test_pred)

                self.models[symbol] = model
                self.scalers[symbol] = scaler
                self.model_metrics[symbol] = {
                    "train_accuracy": float(train_acc),
                    "test_accuracy": float(test_acc),
                    "train_rows": int(len(X_train)),
                    "test_rows": int(len(X_test)),
                }

                trained_count += 1
                print(
                    f"✓ Trained {symbol:<10} | "
                    f"Train: {train_acc:.2%} | Test: {test_acc:.2%}"
                )

            except Exception as e:
                print(f"Training failed for {symbol}: {e}")

        self.save_models()
        print(f"\n✓ Saved {trained_count} trained models to {self.model_path}")

    def _latest_feature_row(self, data):
        df = self.create_features(data)
        if df.empty:
            return None, None
        latest = df.iloc[-1]
        return latest, df

    def generate_signal(self, symbol, asset_class="unknown"):
        try:
            if symbol not in self.models or symbol not in self.scalers:
                print(f"No model/scaler for {symbol}")
                return None

            if not self.feature_cols:
                print("Feature columns not loaded")
                return None

            data = self.get_data(symbol, period_days=400)
            if data.empty or len(data) < 220:
                print(f"Not enough recent data for {symbol}: {len(data)} rows")
                return None

            latest_row, full_df = self._latest_feature_row(data)
            if latest_row is None:
                print(f"Could not build features for {symbol}")
                return None

            feature_array = np.array(
                [latest_row.get(col, 0) for col in self.feature_cols],
                dtype=float
            ).reshape(1, -1)

            if np.any(np.isnan(feature_array)) or np.any(np.isinf(feature_array)):
                print(f"Invalid feature vector for {symbol}")
                return None

            feature_scaled = self.scalers[symbol].transform(feature_array)
            prob_up = float(self.models[symbol].predict_proba(feature_scaled)[0][1])

            # Wider hold zone
            if prob_up >= 0.60:
                signal_label = "BUY"
            elif prob_up <= 0.40:
                signal_label = "SELL"
            else:
                signal_label = "HOLD"

            close = float(data["Close"].iloc[-1])
            sma20 = float(full_df["sma20"].iloc[-1])
            sma50 = float(full_df["sma50"].iloc[-1])
            rsi = float(full_df["rsi"].iloc[-1])
            volatility = float(full_df["volatility_20"].iloc[-1])

            confidence_strength = abs(prob_up - 0.5) * 2  # 0 to 1

            return {
                "symbol": symbol,
                "asset_class": asset_class,
                "price": close,
                "signal": signal_label,
                "prob_up": prob_up,
                "confidence_strength": float(confidence_strength),
                "sma20": sma20,
                "sma50": sma50,
                "rsi": rsi,
                "volatility_20": volatility,
                "train_accuracy": self.model_metrics.get(symbol, {}).get("train_accuracy"),
                "test_accuracy": self.model_metrics.get(symbol, {}).get("test_accuracy"),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Signal generation failed for {symbol}: {e}")
            return None


ASSETS = {
    "stocks": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B",
        "JPM", "V", "MA", "WMT", "COST", "JNJ", "PG", "KO", "PEP", "XOM",
        "CVX", "COP", "HD", "UNH", "ABBV", "MRK", "AMD", "CRM", "ADBE",
        "ORCL", "INTC", "QCOM", "NFLX", "AVGO", "PLTR", "SNOW", "SHOP",
        "NET", "UBER", "COIN", "MSTR", "GS", "MS", "BAC", "C", "PYPL",
        "DIS", "NKE", "CAT", "BA", "GE", "IBM"
    ],
    "etfs": [
        "SPY", "QQQ", "IWM", "DIA", "VTI", "XLK", "XLF", "XLE", "XLV", "XLI",
        "XLP", "XLY", "SMH", "ARKK", "TLT", "GLD", "SLV", "USO"
    ],
    "commodities": [
        "GC=F",   # Gold
        "SI=F",   # Silver
        "CL=F",   # Crude Oil
        "BZ=F",   # Brent
        "NG=F",   # Natural Gas
        "HG=F",   # Copper
        "ZC=F",   # Corn
        "ZW=F",   # Wheat
        "ZS=F",   # Soybeans
        "KC=F",   # Coffee
        "CT=F",   # Cotton
        "SB=F",   # Sugar
        "CC=F",   # Cocoa
        "LE=F",   # Live Cattle
        "HE=F"    # Lean Hogs
    ],
    "forex": [
        "EURUSD=X",
        "GBPUSD=X",
        "AUDUSD=X",
        "NZDUSD=X",
        "USDCAD=X",
        "USDCHF=X",
        "JPY=X",       # USD/JPY on Yahoo
        "EURGBP=X",
        "EURJPY=X",
        "GBPJPY=X",
        "AUDJPY=X",
        "CADJPY=X"
    ],
    "crypto": [
        "BTC-USD",
        "ETH-USD",
        "SOL-USD",
        "XRP-USD",
        "ADA-USD",
        "DOGE-USD",
        "BNB-USD",
        "AVAX-USD",
        "LINK-USD",
        "DOT-USD"
    ]
}


def flatten_assets(asset_map):
    symbols = []
    for items in asset_map.values():
        symbols.extend(items)
    return symbols


def print_section_header(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def main():
    all_symbols = flatten_assets(ASSETS)

    print("=" * 100)
    print(f"DAILY MULTI-ASSET SIGNAL GENERATION - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 100)

    generator = DailySignalGenerator()
    generator.load_or_train_models(all_symbols)

    print(f"\nModels loaded: {len(generator.models)}")
    print(f"Scalers loaded: {len(generator.scalers)}")
    print(f"Feature columns: {len(generator.feature_cols) if generator.feature_cols else 0}")
    print(f"Sample symbols: {list(generator.models.keys())[:10]}")

    all_signals = []
    summary = {}

    for asset_class, symbols in ASSETS.items():
        print_section_header(f"{asset_class.upper()} SIGNALS")
        print(f"{'Symbol':<12} {'Price':>12} {'Signal':>8} {'ProbUp':>10} {'RSI':>8} {'TestAcc':>10}")
        print("-" * 100)

        buy_count = 0
        sell_count = 0
        hold_count = 0
        class_signals = []

        for symbol in symbols:
            signal = generator.generate_signal(symbol, asset_class=asset_class)
            if not signal:
                continue

            class_signals.append(signal)
            all_signals.append(signal)

            if signal["signal"] == "BUY":
                buy_count += 1
            elif signal["signal"] == "SELL":
                sell_count += 1
            else:
                hold_count += 1

            marker = "🔥" if signal["signal"] == "BUY" and signal["prob_up"] >= 0.65 else " "
            test_acc = signal["test_accuracy"] if signal["test_accuracy"] is not None else 0.0

            print(
                f"{marker} {symbol:<10} "
                f"{signal['price']:>12.4f} "
                f"{signal['signal']:>8} "
                f"{signal['prob_up']:>9.1%} "
                f"{signal['rsi']:>8.1f} "
                f"{test_acc:>9.1%}"
            )

        summary[asset_class] = {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "total_signals": len(class_signals),
        }

        print(f"\n{asset_class.upper()} SUMMARY -> BUY: {buy_count} | SELL: {sell_count} | HOLD: {hold_count}")

    # Ranked outputs
    top_buys = sorted(
        [s for s in all_signals if s["signal"] == "BUY"],
        key=lambda x: x["prob_up"],
        reverse=True
    )[:10]

    top_sells = sorted(
        [s for s in all_signals if s["signal"] == "SELL"],
        key=lambda x: x["prob_up"]
    )[:10]

    print_section_header("TOP 10 BUY CANDIDATES")
    if top_buys:
        for s in top_buys:
            print(
                f"{s['symbol']:<12} {s['asset_class']:<12} "
                f"ProbUp={s['prob_up']:.1%}  RSI={s['rsi']:.1f}  TestAcc={s['test_accuracy']:.1%}"
            )
    else:
        print("No BUY candidates today.")

    print_section_header("TOP 10 SELL CANDIDATES")
    if top_sells:
        for s in top_sells:
            print(
                f"{s['symbol']:<12} {s['asset_class']:<12} "
                f"ProbUp={s['prob_up']:.1%}  RSI={s['rsi']:.1f}  TestAcc={s['test_accuracy']:.1%}"
            )
    else:
        print("No SELL candidates today.")

    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "top_buys": top_buys,
        "top_sells": top_sells,
        "signals": all_signals,
        "model_count": len(generator.models),
        "feature_count": len(generator.feature_cols) if generator.feature_cols else 0,
    }

    with open("daily_signals.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n✓ Saved signals to: daily_signals.json")
    print("=== READY FOR TOMORROW ===")


if __name__ == "__main__":
    main()