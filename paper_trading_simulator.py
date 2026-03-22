import backtrader as bt
import yfinance as yf
import pandas as pd
import numpy as np
import pickle
import warnings

warnings.filterwarnings("ignore")

# =========================
# LOAD MODELS
# =========================
with open("stock_specific_models.pkl", "rb") as f:
    models_dict = pickle.load(f)


# =========================
# FEATURE ENGINEERING
# =========================
def compute_rsi(close, period=14):
    close = np.asarray(close, dtype=float)
    if len(close) < period + 1:
        return 50.0

    delta = np.diff(close)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_atr(high, low, close, period=14):
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)

    if len(close) < period + 1:
        return 0.0

    prev_close = close[:-1]
    high_curr = high[1:]
    low_curr = low[1:]

    tr1 = high_curr - low_curr
    tr2 = np.abs(high_curr - prev_close)
    tr3 = np.abs(low_curr - prev_close)

    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    return float(np.mean(tr[-period:]))


def safe_mean(arr):
    arr = np.asarray(arr, dtype=float)
    return float(np.mean(arr)) if len(arr) > 0 else 0.0


def safe_std(arr):
    arr = np.asarray(arr, dtype=float)
    return float(np.std(arr)) if len(arr) > 0 else 0.0


def build_feature_map(close, high, low, open_, volume):
    close = np.asarray(close, dtype=float)
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    open_ = np.asarray(open_, dtype=float)
    volume = np.asarray(volume, dtype=float)

    returns = np.diff(close) / close[:-1] * 100 if len(close) > 1 else np.array([])

    sma5 = safe_mean(close[-5:])
    sma10 = safe_mean(close[-10:])
    sma20 = safe_mean(close[-20:])
    sma50 = safe_mean(close[-50:]) if len(close) >= 50 else safe_mean(close)

    vol10 = safe_std(returns[-10:])
    vol20 = safe_std(returns[-20:])

    rsi = compute_rsi(close, period=14)
    atr = compute_atr(high, low, close, period=14)

    volume_ma = safe_mean(volume[-20:]) if len(volume) >= 20 else safe_mean(volume)
    volume_ratio = volume[-1] / volume_ma if volume_ma != 0 else 1.0

    momentum_5 = close[-1] - close[-6] if len(close) >= 6 else 0.0
    momentum_10 = close[-1] - close[-11] if len(close) >= 11 else 0.0

    rolling_mean_20 = sma20
    rolling_std_20 = safe_std(close[-20:])
    zscore = (close[-1] - rolling_mean_20) / rolling_std_20 if rolling_std_20 != 0 else 0.0

    feature_map = {
        # returns
        "returns_1d": float(returns[-1]) if len(returns) >= 1 else 0.0,
        "returns_5d": safe_mean(returns[-5:]),
        "returns_10d": safe_mean(returns[-10:]),

        # price structure
        "high_low_ratio": float(high[-1] / low[-1]) if low[-1] != 0 else 1.0,
        "close_open_ratio": float(close[-1] / open_[-1]) if open_[-1] != 0 else 1.0,
        "price_range": float(high[-1] - low[-1]),

        # moving averages
        "sma5": sma5,
        "sma10": sma10,
        "sma20": sma20,
        "sma50": sma50,

        # relative to moving averages
        "close_above_sma5": float(close[-1] > sma5),
        "close_above_sma10": float(close[-1] > sma10),
        "close_above_sma20": float(close[-1] > sma20),
        "close_above_sma50": float(close[-1] > sma50),

        # MA relationships
        "sma5_above_sma10": float(sma5 > sma10),
        "sma10_above_sma20": float(sma10 > sma20),
        "sma20_above_sma50": float(sma20 > sma50),

        # momentum / trend
        "momentum_5": float(momentum_5),
        "momentum_10": float(momentum_10),

        # volatility
        "volatility_10": vol10,
        "volatility_20": vol20,

        # indicators
        "rsi": float(rsi),
        "atr": float(atr),

        # volume
        "volume": float(volume[-1]),
        "volume_ma": float(volume_ma),
        "volume_ratio": float(volume_ratio),

        # breakout / range features
        "highest_10": float(np.max(high[-10:])) if len(high) >= 10 else float(np.max(high)),
        "lowest_10": float(np.min(low[-10:])) if len(low) >= 10 else float(np.min(low)),
        "breakout_10": float(close[-1] > np.max(high[-10:-1])) if len(high) >= 10 else 0.0,
        "breakdown_10": float(close[-1] < np.min(low[-10:-1])) if len(low) >= 10 else 0.0,

        # statistical
        "zscore": float(zscore),

        # raw OHLC in case training included them
        "Close": float(close[-1]),
        "High": float(high[-1]),
        "Low": float(low[-1]),
        "Open": float(open_[-1]),
    }

    return feature_map


# =========================
# STRATEGY
# =========================
class PaperTradingStrategy(bt.Strategy):
    params = (
        ("model", None),
        ("scaler", None),
        ("feature_cols", None),
        ("entry_threshold", 0.52),
        ("exit_threshold", 0.48),
        ("stop_loss", 0.02),
        ("take_profit", 0.03),
        ("printlog", True),
    )

    def __init__(self):
        self.model = self.p.model
        self.scaler = self.p.scaler
        self.feature_cols = self.p.feature_cols

        self.order = None
        self.entry_price = None

        # metrics
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        self.max_drawdown = 0.0
        self.peak_value = self.broker.getvalue()

    def log(self, txt):
        if self.p.printlog:
            dt = self.datas[0].datetime.date(0)
            print(f"{dt} | {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.log(
                    f"BUY EXECUTED | Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size}"
                )
            elif order.issell():
                self.log(
                    f"SELL EXECUTED | Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size}"
                )
            self.order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("ORDER FAILED")
            self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.trades_count += 1
        if trade.pnlcomm > 0:
            self.wins += 1
        else:
            self.losses += 1

        self.log(
            f"TRADE CLOSED | Gross PnL: {trade.pnl:.2f}, Net PnL: {trade.pnlcomm:.2f}"
        )

    def next(self):
        # drawdown tracking
        current_value = self.broker.getvalue()
        if current_value > self.peak_value:
            self.peak_value = current_value

        drawdown = (self.peak_value - current_value) / self.peak_value
        self.max_drawdown = max(self.max_drawdown, drawdown)

        # don't overlap orders
        if self.order:
            return

        # need enough history for longer features
        if len(self) < 60:
            return

        try:
            lookback = min(len(self), 60)

            close = np.array(self.data.close.get(size=lookback), dtype=float)
            high = np.array(self.data.high.get(size=lookback), dtype=float)
            low = np.array(self.data.low.get(size=lookback), dtype=float)
            open_ = np.array(self.data.open.get(size=lookback), dtype=float)
            volume = np.array(self.data.volume.get(size=lookback), dtype=float)

            if (
                len(close) < 20
                or np.any(np.isnan(close))
                or np.any(np.isnan(high))
                or np.any(np.isnan(low))
                or np.any(np.isnan(open_))
                or np.any(np.isnan(volume))
            ):
                return

            feature_map = build_feature_map(close, high, low, open_, volume)

            # build features in exact training order
            features = np.array(
                [[feature_map.get(col, 0.0) for col in self.feature_cols]],
                dtype=float,
            )

            features_scaled = self.scaler.transform(features)
            prediction_prob = float(self.model.predict_proba(features_scaled)[0][1])

            self.log(
                f"Close: {close[-1]:.2f} | Prob: {prediction_prob:.3f} | "
                f"Position: {'LONG' if self.position else 'FLAT'}"
            )

            # entry
            if not self.position:
                if prediction_prob > self.p.entry_threshold:
                    cash = self.broker.getcash()
                    size = int((cash * 0.95) / close[-1])

                    if size > 0:
                        self.order = self.buy(size=size)

            # exit
            else:
                current_price = close[-1]

                # model exit
                if prediction_prob < self.p.exit_threshold:
                    self.order = self.sell(size=self.position.size)

                # stop loss
                elif self.entry_price and current_price <= self.entry_price * (1 - self.p.stop_loss):
                    self.order = self.sell(size=self.position.size)

                # take profit
                elif self.entry_price and current_price >= self.entry_price * (1 + self.p.take_profit):
                    self.order = self.sell(size=self.position.size)

        except Exception as e:
            self.log(f"ERROR in next(): {e}")


# =========================
# MAIN
# =========================
print("=== PAPER TRADING SIMULATOR ===\n")

stocks_to_test = [
    ("SPY", models_dict["SPY"]),
    ("QQQ", models_dict["QQQ"]),
    ("EEM", models_dict["EEM"]),
]

print(f"{'Stock':<10} {'Starting':<12} {'Final':<12} {'Return':<12} {'Trades':<10} {'Win Rate':<12} {'Max DD'}")
print("-" * 90)

for ticker, model_data in stocks_to_test:
    try:
        data = yf.download(ticker, start="2024-01-01", end="2024-12-31", progress=False)

        if data.empty or len(data) < 60:
            print(f"{ticker:<10} Not enough data")
            continue

        # handle multi-index columns from yfinance if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        # Backtrader expects title-case default names unless custom lines,
        # so rename back for PandasData compatibility
        data = data.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )

        cerebro = bt.Cerebro()
        cerebro.addstrategy(
            PaperTradingStrategy,
            model=model_data["model"],
            scaler=model_data["scaler"],
            feature_cols=model_data["feature_cols"],
            entry_threshold=0.52,   # lowered slightly to test live behavior
            exit_threshold=0.48,
            printlog=False,         # change to True for debugging
        )

        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed, name=ticker)

        cerebro.broker.setcash(10000)
        cerebro.broker.setcommission(commission=0.001)

        strats = cerebro.run()
        strat = strats[0]

        final_value = cerebro.broker.getvalue()
        total_return = (final_value - 10000) / 10000 * 100
        win_rate = (strat.wins / strat.trades_count * 100) if strat.trades_count > 0 else 0.0

        print(
            f"{ticker:<10} $10,000     ${final_value:>10,.0f} "
            f"{total_return:>10.2f}% {strat.trades_count:<10} "
            f"{win_rate:>10.1f}% {strat.max_drawdown*100:>6.2f}%"
        )

    except Exception as e:
        print(f"{ticker:<10} Error: {str(e)[:80]}")

print("\n" + "=" * 90)
print("KEY METRICS FOR FUNDED TRADING")
print("=" * 90)
print("""
Funded traders look for:
✓ Positive returns (even small is good)
✓ Win rate > 45%
✓ Max drawdown < 20%
✓ Consistent performance
✓ Low correlation to market
""")

print("\n=== SESSION COMPLETE ===")
print("Paper trading simulator fixed and ready for testing")