# Day 12: Ultimate Adaptive Live Trading System
# Fixed version: robust yfinance handling, valid tickers, proper error reporting,
# separate training/live feature pipeline

import yfinance as yf
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings("ignore")

print("=== ULTIMATE ADAPTIVE LIVE TRADING SYSTEM ===\n")


class UltimateTrader:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_cols = {}
        self.performance_log = []

    def normalize_columns(self, df):
        """Flatten yfinance MultiIndex columns if needed"""
        if df is None or df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df

    def download_data(self, ticker, days=180):
        """Robust Yahoo Finance download"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                auto_adjust=False,
                progress=False,
                threads=False,
            )

            if data is None or data.empty:
                print(f"    No data returned for {ticker}")
                return None

            data = self.normalize_columns(data)

            required_cols = ["Open", "High", "Low", "Close", "Volume"]
            missing = [c for c in required_cols if c not in data.columns]
            if missing:
                print(f"    Missing columns for {ticker}: {missing}")
                return None

            data = data[required_cols].copy()
            data = data.dropna()

            if data.empty:
                print(f"    Data empty after cleaning for {ticker}")
                return None

            return data

        except Exception as e:
            print(f"    Download error for {ticker}: {e}")
            return None

    def create_features(self, data, include_target=True):
        """Create ML features from OHLCV"""
        df = data.copy()
        df = self.normalize_columns(df)

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna().copy()

        # Need enough raw rows for 50-day SMA and other rolling features
        if len(df) < 60:
            raise ValueError("Not enough raw rows to build features")

        # Returns
        df["returns_1d"] = df["Close"].pct_change() * 100
        df["returns_5d"] = df["Close"].pct_change(5) * 100
        df["returns_10d"] = df["Close"].pct_change(10) * 100

        # Price structure
        df["high_low_ratio"] = (df["High"] - df["Low"]) / df["Close"] * 100
        df["close_open_ratio"] = (df["Close"] - df["Open"]) / df["Close"] * 100
        df["price_range"] = (df["High"] - df["Low"]) / df["Close"]

        # Moving averages
        for period in [5, 10, 20, 50]:
            df[f"sma{period}"] = df["Close"].rolling(period).mean()
            df[f"close_above_sma{period}"] = (df["Close"] > df[f"sma{period}"]).astype(int)

        # SMA slopes
        prev_sma10 = df["sma10"].shift(1)
        prev_sma20 = df["sma20"].shift(1)
        df["sma_slope_10"] = np.where(
            prev_sma10 != 0,
            (df["sma10"] - prev_sma10) / prev_sma10 * 100,
            0
        )
        df["sma_slope_20"] = np.where(
            prev_sma20 != 0,
            (df["sma20"] - prev_sma20) / prev_sma20 * 100,
            0
        )

        # Volatility
        df["volatility_10"] = df["returns_1d"].rolling(10).std()
        df["volatility_20"] = df["returns_1d"].rolling(20).std()

        # ATR
        df["atr"] = (df["High"] - df["Low"]).rolling(14).mean()
        df["atr_percent"] = df["atr"] / df["Close"] * 100

        # ROC
        df["roc_5"] = (df["Close"] - df["Close"].shift(5)) / df["Close"].shift(5) * 100
        df["roc_10"] = (df["Close"] - df["Close"].shift(10)) / df["Close"].shift(10) * 100

        # Momentum
        df["momentum_5"] = df["Close"].diff(5)
        df["momentum_10"] = df["Close"].diff(10)

        # RSI
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # Volume
        df["volume_ma"] = df["Volume"].rolling(20).mean()
        df["volume_ratio"] = df["Volume"] / df["volume_ma"]

        # Trend structure
        df["higher_high"] = (df["High"] > df["High"].shift(1)).astype(int)
        df["higher_low"] = (df["Low"] > df["Low"].shift(1)).astype(int)
        df["lower_high"] = (df["High"] < df["High"].shift(1)).astype(int)
        df["lower_low"] = (df["Low"] < df["Low"].shift(1)).astype(int)

        # Mean reversion
        df["distance_from_ma"] = (df["Close"] - df["sma20"]) / df["sma20"] * 100
        df["zscore"] = np.where(
            df["volatility_20"] != 0,
            df["distance_from_ma"] / df["volatility_20"],
            0
        )

        # Only create target for training
        if include_target:
            df["target"] = (df["returns_1d"].shift(-1) > 0).astype(int)

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna().copy()

        if include_target:
            if len(df) < 30:
                raise ValueError("Not enough rows after feature engineering for training")
        else:
            if len(df) < 1:
                raise ValueError("No valid live feature rows available")

        return df

    def retrain_model(self, ticker):
        """Retrain model on latest historical data"""
        try:
            data = self.download_data(ticker, days=240)
            if data is None or len(data) < 80:
                print(f"    Not enough raw data for {ticker}")
                return None

            df = self.create_features(data, include_target=True)

            exclude_cols = ["Open", "High", "Low", "Close", "Volume", "target"]
            feature_cols = [col for col in df.columns if col not in exclude_cols]

            X = df[feature_cols].astype(float).values
            y = df["target"].astype(int).values

            if len(np.unique(y)) < 2:
                print(f"    Only one target class for {ticker}")
                return None

            split_idx = int(len(df) * 0.8)
            if split_idx < 20 or len(df) - split_idx < 5:
                print(f"    Not enough rows for train/test split on {ticker}")
                return None

            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_leaf=3,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(X_train_scaled, y_train)

            accuracy = model.score(X_test_scaled, y_test)

            self.models[ticker] = model
            self.scalers[ticker] = scaler
            self.feature_cols[ticker] = feature_cols

            return accuracy

        except Exception as e:
            print(f"    Training error for {ticker}: {e}")
            return None

    def generate_signal(self, ticker):
        """Generate trading signal for ticker"""
        try:
            if ticker not in self.models:
                print(f"    No trained model for {ticker}")
                return None

            # Use more history so rolling features are safe
            data = self.download_data(ticker, days=180)
            if data is None or len(data) < 60:
                print(f"    Not enough live data for {ticker}")
                return None

            df = self.create_features(data, include_target=False)
            latest = df.iloc[-1]

            feature_cols = self.feature_cols[ticker]
            X_live = latest[feature_cols].astype(float).values.reshape(1, -1)
            X_live_scaled = self.scalers[ticker].transform(X_live)

            prob = self.models[ticker].predict_proba(X_live_scaled)[0][1]

            if prob > 0.55:
                decision = "BUY"
            elif prob < 0.45:
                decision = "SELL"
            else:
                decision = "HOLD"

            signal = {
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "price": float(latest["Close"]),
                "signal": decision,
                "confidence": float(prob),
                "sma20": float(latest["sma20"]),
                "rsi": float(latest["rsi"]),
                "volatility": float(latest["volatility_20"]),
            }

            return signal

        except Exception as e:
            print(f"    Signal generation error for {ticker}: {e}")
            return None


print("=" * 80)
print("ULTIMATE ADAPTIVE LIVE TRADING SYSTEM - 30+ STOCKS")
print("=" * 80)

trader = UltimateTrader()

stocks = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "BRK-B",
    "JPM",
    "V",
    "WMT",
    "JNJ",
    "PG",
    "AMD",
    "CRM",
    "SNOW",
    "NET",
    "SHOP",
    "XYZ",
    "GS",
    "C",
    "COIN",
    "MSTR",
    "XOM",
    "CVX",
    "COP",
    "SPY",
    "QQQ",
    "IWM",
]

# Train models
print("\n1. TRAINING STOCK MODELS (latest ~8 months of data):")
print("-" * 80)

successful = 0
failed = 0

for i, ticker in enumerate(stocks, 1):
    print(f"{i:2d}. {ticker:8s}", end=" ")
    accuracy = trader.retrain_model(ticker)

    if accuracy is not None:
        print(f"✓ {accuracy:.1%}")
        successful += 1
    else:
        print("✗")
        failed += 1

print(f"\nTraining complete: {successful}/{len(stocks)} successful")

# Generate signals
print("\n2. GENERATING TODAY'S SIGNALS FOR ALL STOCKS:")
print("-" * 80)
print(f"\n{'Ticker':<8} {'Price':>10} {'Signal':>7} {'Confidence':>12} {'RSI':>6} {'Volatility':>10}")
print("-" * 80)

signals = []
buy_signals = 0
sell_signals = 0
hold_signals = 0
buy_high_conf = 0

for ticker in stocks:
    signal = trader.generate_signal(ticker)
    if signal:
        signals.append(signal)

        if signal["signal"] == "BUY":
            buy_signals += 1
            if signal["confidence"] > 0.60:
                buy_high_conf += 1
                marker = "🔥"
            else:
                marker = "↑"
        elif signal["signal"] == "SELL":
            sell_signals += 1
            marker = "↓"
        else:
            hold_signals += 1
            marker = "→"

        print(
            f"{marker} {ticker:<6s} "
            f"${signal['price']:>9.2f} "
            f"{signal['signal']:>7s} "
            f"{signal['confidence']:>11.1%} "
            f"{signal['rsi']:>6.0f} "
            f"{signal['volatility']:>9.2f}%"
        )

# Save signals
with open("ultimate_signals.json", "w") as f:
    json.dump(signals, f, indent=2)

# Save models
with open("ultimate_trading_models.pkl", "wb") as f:
    pickle.dump(
        {
            "models": trader.models,
            "scalers": trader.scalers,
            "feature_cols": trader.feature_cols,
        },
        f,
    )

print("\n" + "=" * 80)
print("TODAY'S TRADING SUMMARY")
print("=" * 80)
print(f"\nTotal signals: {len(signals)}")
print(f"  🔥 Strong BUY (>60% confidence): {buy_high_conf}")
print(f"  ↑  BUY: {buy_signals}")
print(f"  ↓  SELL: {sell_signals}")
print(f"  →  HOLD: {hold_signals}")

strong_buys = [s for s in signals if s["signal"] == "BUY" and s["confidence"] > 0.60]
buys = [s for s in signals if s["signal"] == "BUY" and s["confidence"] <= 0.60]

aggressive_deployed = 10000 * len(strong_buys) + 5000 * len(buys)
aggressive_cash = max(0, 100000 - aggressive_deployed)

print(f"\n" + "=" * 80)
print("RECOMMENDED PORTFOLIO ALLOCATION (100k account)")
print("=" * 80)

print(f"""
AGGRESSIVE APPROACH:
- Allocate to all {len(strong_buys)} strong BUY signals: ${10000 * len(strong_buys):,.0f}
- Add {len(buys)} regular BUY signals: ${5000 * len(buys):,.0f}
- Total long exposure: ${aggressive_deployed:,.0f}
- Cash buffer: ${aggressive_cash:,.0f}

CONSERVATIVE APPROACH:
- Only strong BUY signals (>60% confidence): ${5000 * len(strong_buys):,.0f}
- Avoid SELL signals
- Keep most capital in cash / short-duration bonds

SUGGESTED (BALANCED):
Position sizing:
- Each strong BUY: $5,000-10,000
- Each regular BUY: $2,000-5,000
- Total: 40-60% deployed, remainder in cash buffer
""")

print(f"✓ Signals saved to: ultimate_signals.json")
print(f"✓ Models saved to: ultimate_trading_models.pkl")
print(f"✓ System monitoring {len(stocks)} symbols")
print(f"\n=== ULTIMATE LIVE TRADING SYSTEM OPERATIONAL ===")