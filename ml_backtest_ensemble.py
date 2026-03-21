import backtrader as bt
import yfinance as yf
import pandas as pd
import numpy as np
import pickle
import warnings

warnings.filterwarnings("ignore")

# =========================
# Load trained models
# =========================
with open("ensemble_models.pkl", "rb") as f:
    models = pickle.load(f)

rf_model = models["rf_model"]
scaler = models["scaler"]
feature_cols = models["feature_cols"]

print("Loaded model expects", len(feature_cols), "features")
print("Feature columns:")
for i, col in enumerate(feature_cols, 1):
    print(f"{i:>2}. {col}")
print()


# =========================
# Strategies
# =========================
class MLEnsembleStrategy(bt.Strategy):
    params = dict(confidence_threshold=0.55, printlog=False)

    def __init__(self, rf_model, scaler, feature_cols):
        self.rf_model = rf_model
        self.scaler = scaler
        self.feature_cols = feature_cols
        self.trades = 0
        self.high_confidence_trades = 0

    def log(self, txt):
        if self.params.printlog:
            dt = self.datas[0].datetime.date(0)
            print(f"{dt} - {txt}")

    def next(self):
        if len(self.data) < 21:
            return

        try:
            close = np.array(self.data.close.get(size=21), dtype=float)
            high = np.array(self.data.high.get(size=21), dtype=float)
            low = np.array(self.data.low.get(size=21), dtype=float)
            open_ = np.array(self.data.open.get(size=21), dtype=float)
            volume = np.array(self.data.volume.get(size=21), dtype=float)

            if len(close) < 21 or np.any(np.isnan(close)):
                return

            # =========================
            # Feature calculations
            # =========================
            returns_1d = (close[-1] - close[-2]) / close[-2] * 100 if close[-2] != 0 else 0
            returns_5d = (close[-1] - close[-6]) / close[-6] * 100 if close[-6] != 0 else 0
            returns_10d = (close[-1] - close[-11]) / close[-11] * 100 if close[-11] != 0 else 0

            high_low_ratio = (high[-1] - low[-1]) / close[-1] * 100 if close[-1] != 0 else 0
            close_open_ratio = (close[-1] - open_[-1]) / close[-1] * 100 if close[-1] != 0 else 0
            price_range = (high[-1] - low[-1]) / close[-1] if close[-1] != 0 else 0

            sma5 = np.mean(close[-5:])
            sma10 = np.mean(close[-10:])
            sma20 = np.mean(close[-20:])
            sma50 = np.mean(close[-21:])  # keep as trained compatibility placeholder

            close_above_sma5 = 1 if close[-1] > sma5 else 0
            close_above_sma10 = 1 if close[-1] > sma10 else 0
            close_above_sma20 = 1 if close[-1] > sma20 else 0
            close_above_sma50 = 1 if close[-1] > sma50 else 0

            sma_slope_10 = (close[-10] - close[-11]) / close[-11] * 100 if close[-11] != 0 else 0
            sma_slope_20 = (close[-20] - close[-21]) / close[-21] * 100 if close[-21] != 0 else 0

            returns10 = np.diff(close[-10:]) / close[-10:-1] * 100
            returns20 = np.diff(close[-20:]) / close[-20:-1] * 100
            volatility_10 = np.std(returns10) if len(returns10) > 0 else 0
            volatility_20 = np.std(returns20) if len(returns20) > 0 else 0

            atr = np.mean(high[-14:] - low[-14:])
            atr_percent = atr / close[-1] * 100 if close[-1] != 0 else 0

            roc_5 = (close[-1] - close[-6]) / close[-6] * 100 if close[-6] != 0 else 0
            roc_10 = (close[-1] - close[-11]) / close[-11] * 100 if close[-11] != 0 else 0

            momentum_5 = close[-1] - close[-6]
            momentum_10 = close[-1] - close[-11]

            delta = np.diff(close)
            gains = delta[delta > 0]
            losses = -delta[delta < 0]

            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0

            if avg_loss == 0 and avg_gain == 0:
                rsi = 50
            elif avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            volume_ma = np.mean(volume[-20:]) if np.all(np.isfinite(volume[-20:])) else 1
            volume_ratio = volume[-1] / volume_ma if volume_ma > 0 else 1

            higher_high = 1 if high[-1] > high[-2] else 0
            higher_low = 1 if low[-1] > low[-2] else 0
            lower_high = 1 if high[-1] < high[-2] else 0
            lower_low = 1 if low[-1] < low[-2] else 0

            distance_from_ma = (close[-1] - sma20) / sma20 * 100 if sma20 != 0 else 0
            zscore = distance_from_ma / volatility_20 if volatility_20 > 0 else 0

            # =========================
            # EXACT feature names from training
            # =========================
            feature_dict = {
                "High": high[-1],
                "Low": low[-1],
                "Open": open_[-1],
                "Volume": volume[-1],
                "returns_1d": returns_1d,
                "returns_5d": returns_5d,
                "returns_10d": returns_10d,
                "high_low_ratio": high_low_ratio,
                "close_open_ratio": close_open_ratio,
                "price_range": price_range,
                "sma5": sma5,
                "close_above_sma5": close_above_sma5,
                "sma10": sma10,
                "close_above_sma10": close_above_sma10,
                "sma20": sma20,
                "close_above_sma20": close_above_sma20,
                "sma50": sma50,
                "close_above_sma50": close_above_sma50,
                "sma_slope_10": sma_slope_10,
                "sma_slope_20": sma_slope_20,
                "volatility_10": volatility_10,
                "volatility_20": volatility_20,
                "atr": atr,
                "atr_percent": atr_percent,
                "roc_5": roc_5,
                "roc_10": roc_10,
                "momentum_5": momentum_5,
                "momentum_10": momentum_10,
                "rsi": rsi,
                "volume_ma": volume_ma,
                "volume_ratio": volume_ratio,
                "higher_high": higher_high,
                "higher_low": higher_low,
                "lower_high": lower_high,
                "lower_low": lower_low,
                "distance_from_ma": distance_from_ma,
                "zscore": zscore,
            }

            missing_features = [col for col in self.feature_cols if col not in feature_dict]
            if missing_features:
                raise ValueError(f"Missing trained features in strategy: {missing_features}")

            features = np.array(
                [feature_dict[col] for col in self.feature_cols],
                dtype=float
            ).reshape(1, -1)

            if np.any(~np.isfinite(features)):
                raise ValueError("Feature vector contains NaN or infinite values")

            features_scaled = self.scaler.transform(features)
            prediction_prob = self.rf_model.predict_proba(features_scaled)[0][1]

            if not self.position:
                if prediction_prob > self.params.confidence_threshold:
                    size = int(self.broker.getcash() / self.data.close[0])
                    if size > 0:
                        self.buy(size=size)
                        self.trades += 1
                        self.high_confidence_trades += 1
                        self.log(f"BUY | Prob={prediction_prob:.3f} | Size={size}")
            else:
                if prediction_prob < (1 - self.params.confidence_threshold):
                    self.sell(size=self.position.size)
                    self.log(f"SELL | Prob={prediction_prob:.3f} | Size={self.position.size}")

        except Exception as e:
            print(
                f"[ERROR] {self.data._name if hasattr(self.data, '_name') else 'DATA'} | "
                f"{self.data.datetime.date(0)} | {e}"
            )
            raise


class BuyHoldStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            size = int(self.broker.getcash() / self.data.close[0])
            if size > 0:
                self.buy(size=size)


# =========================
# Helpers
# =========================
def download_data(ticker, start="2023-01-01", end="2023-12-31"):
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)

    if data is None or data.empty:
        raise ValueError(f"No data downloaded for {ticker}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        raise ValueError(f"{ticker} missing required columns: {missing}")

    data = data[required_cols].dropna()

    if len(data) < 50:
        raise ValueError(f"Not enough data for {ticker}. Rows: {len(data)}")

    return data


def run_ml_backtest(data, ticker):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        MLEnsembleStrategy,
        rf_model=rf_model,
        scaler=scaler,
        feature_cols=feature_cols,
        printlog=False,
    )

    data_feed = bt.feeds.PandasData(dataname=data, name=ticker)
    cerebro.adddata(data_feed)

    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)

    strats = cerebro.run()
    strat = strats[0]

    final_value = cerebro.broker.getvalue()
    total_return = (final_value - 10000.0) / 10000.0 * 100

    return total_return, final_value, strat.trades


def run_buyhold_backtest(data, ticker):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BuyHoldStrategy)

    data_feed = bt.feeds.PandasData(dataname=data, name=ticker)
    cerebro.adddata(data_feed)

    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.run()

    final_value = cerebro.broker.getvalue()
    total_return = (final_value - 10000.0) / 10000.0 * 100

    return total_return, final_value


# =========================
# Main
# =========================
if __name__ == "__main__":
    print("=== ML ENSEMBLE BACKTEST ON MULTIPLE STOCKS ===\n")

    stocks = ["SPY", "QQQ", "IWM", "GLD", "TLT", "EEM"]

    print(f"{'Stock':<10} {'ML Return':<15} {'Buy&Hold':<15} {'Difference':<15} {'Winner':<12} {'Trades'}")
    print("-" * 85)

    ml_wins = 0
    completed = 0

    for ticker in stocks:
        try:
            data = download_data(ticker, start="2023-01-01", end="2023-12-31")

            ml_return, ml_final, ml_trades = run_ml_backtest(data, ticker)
            bh_return, bh_final = run_buyhold_backtest(data, ticker)

            diff = ml_return - bh_return
            winner = "ML" if ml_return > bh_return else "B&H"

            if ml_return > bh_return:
                ml_wins += 1

            completed += 1

            print(
                f"{ticker:<10} "
                f"{ml_return:>13.2f}% "
                f"{bh_return:>13.2f}% "
                f"{diff:>13.2f}% "
                f"{winner:<12} "
                f"{ml_trades:>6}"
            )

        except Exception as e:
            print(f"{ticker:<10} Error: {str(e)}")

    print("\n" + "=" * 85)
    print("VERDICT")
    print("=" * 85)
    print(f"\nML Ensemble wins: {ml_wins}/{completed if completed > 0 else len(stocks)} stocks")

    if completed == 0:
        print("No valid backtests completed.")
    elif ml_wins >= 4:
        print("✓ EXCELLENT! ML strategy beats buy & hold!")
        print("Ready for funded trading consideration")
    elif ml_wins >= 2:
        print("~ Partial success: Works on some stocks")
        print("Needs refinement")
    else:
        print("✗ ML needs more work")

    print("\n=== SESSION 3 & 4 COMPLETE ===")