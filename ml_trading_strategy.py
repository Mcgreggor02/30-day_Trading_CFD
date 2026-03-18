import backtrader as bt
import yfinance as yf
import numpy as np
import pandas as pd
import warnings

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

print("=== IMPROVED MACHINE LEARNING TRADING STRATEGY ===\n")

# -----------------------------
# CONFIG
# -----------------------------
TRAIN_START = "2018-01-01"
TRAIN_END   = "2022-12-31"
TEST_START  = "2023-01-01"
TEST_END    = "2023-12-31"

INITIAL_CASH = 10000

# Mixed universe: ETFs + stocks
UNIVERSE = [
    # ETFs
    "SPY", "QQQ", "IWM", "GLD", "TLT", "EEM",
    # Mega-cap / liquid stocks
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL",
    # Other liquid names
    "JPM", "XOM", "UNH", "AMD", "TSLA"
]


# -----------------------------
# DATA HELPERS
# -----------------------------
def download_data(ticker, start, end):
    """
    Explicitly set auto_adjust to avoid ambiguity.
    """
    df = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
        threads=False,
    )

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns=str.title)
    df = df.dropna().copy()

    if df.empty:
        return df

    # Ensure expected columns exist
    needed = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"{ticker}: missing columns {missing}")

    return df


def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()
    return atr


def create_features(df, horizon=5):
    """
    Better, scale-free features.
    """
    out = df.copy()

    close = out["Close"]
    volume = out["Volume"]

    out["ret_1"] = close.pct_change(1)
    out["ret_3"] = close.pct_change(3)
    out["ret_5"] = close.pct_change(5)
    out["ret_10"] = close.pct_change(10)

    out["sma_10"] = close.rolling(10).mean()
    out["sma_20"] = close.rolling(20).mean()
    out["sma_50"] = close.rolling(50).mean()
    out["sma_100"] = close.rolling(100).mean()
    out["sma_200"] = close.rolling(200).mean()

    # Relative trend features
    out["dist_sma10"] = close / out["sma_10"] - 1
    out["dist_sma20"] = close / out["sma_20"] - 1
    out["dist_sma50"] = close / out["sma_50"] - 1
    out["dist_sma200"] = close / out["sma_200"] - 1
    out["sma10_sma20"] = out["sma_10"] / out["sma_20"] - 1
    out["sma20_sma50"] = out["sma_20"] / out["sma_50"] - 1
    out["sma50_sma200"] = out["sma_50"] / out["sma_200"] - 1

    # Range / volatility
    out["range_pct"] = (out["High"] - out["Low"]) / close
    out["atr_14"] = compute_atr(out, 14)
    out["atr_pct"] = out["atr_14"] / close
    out["vol_20"] = out["ret_1"].rolling(20).std()

    # Momentum / oscillator
    out["rsi_14"] = compute_rsi(close, 14)

    # Volume features
    out["vol_ma20"] = volume.rolling(20).mean()
    out["vol_ratio"] = volume / out["vol_ma20"]

    # Forward target: next 5-day direction
    out["fwd_ret"] = close.shift(-horizon) / close - 1
    out["target"] = (out["fwd_ret"] > 0).astype(int)

    # Regime label for filtering
    out["bull_regime"] = (close > out["sma_200"]).astype(int)

    feature_cols = [
        "ret_1", "ret_3", "ret_5", "ret_10",
        "dist_sma10", "dist_sma20", "dist_sma50", "dist_sma200",
        "sma10_sma20", "sma20_sma50", "sma50_sma200",
        "range_pct", "atr_pct", "vol_20",
        "rsi_14", "vol_ratio"
    ]

    out = out.dropna().copy()
    return out, feature_cols


def build_training_set(symbols, start, end):
    frames = []
    feature_cols = None

    for ticker in symbols:
        try:
            df = download_data(ticker, start, end)
            if df.empty:
                print(f"Skipping {ticker}: empty train data")
                continue

            feat_df, cols = create_features(df)
            feat_df["Ticker"] = ticker
            frames.append(feat_df)

            if feature_cols is None:
                feature_cols = cols
        except Exception as e:
            print(f"Skipping {ticker}: {e}")

    if not frames:
        raise ValueError("No training data available.")

    all_data = pd.concat(frames, axis=0).sort_index()
    return all_data, feature_cols


def train_model(train_df, feature_cols):
    X = train_df[feature_cols].values
    y = train_df["target"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=8,
        min_samples_leaf=10,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_scaled, y)

    return model, scaler


def add_predictions(df, model, scaler, feature_cols, prob_threshold=0.55):
    """
    Precompute model predictions in pandas so train/test features are identical.
    """
    X = df[feature_cols].values
    X_scaled = scaler.transform(X)

    probs = model.predict_proba(X_scaled)[:, 1]
    preds = (probs >= prob_threshold).astype(int)

    out = df.copy()
    out["ml_prob"] = probs
    out["signal"] = preds

    # Only allow longs in bull regime
    out["signal"] = np.where(out["bull_regime"] == 1, out["signal"], 0)

    return out


# -----------------------------
# BACKTRADER FEED
# -----------------------------
class MLDataFeed(bt.feeds.PandasData):
    """
    Add precomputed ML columns to Backtrader.
    """
    lines = ("signal", "ml_prob", "atr_14", "sma_50", "sma_200")
    params = (
        ("signal", -1),
        ("ml_prob", -1),
        ("atr_14", -1),
        ("sma_50", -1),
        ("sma_200", -1),
    )


# -----------------------------
# STRATEGY
# -----------------------------
class ImprovedMLStrategy(bt.Strategy):
    params = dict(
        risk_per_trade=0.01,      # 1% account risk
        atr_stop_mult=2.0,
        atr_trail_mult=3.0,
        max_allocation=0.95,      # do not use 100% of cash
        min_prob=0.55
    )

    def __init__(self):
        self.signal = self.datas[0].signal
        self.ml_prob = self.datas[0].ml_prob
        self.atr = self.datas[0].atr_14
        self.sma50 = self.datas[0].sma_50
        self.sma200 = self.datas[0].sma_200

        self.entry_price = None
        self.stop_price = None
        self.highest_price = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.highest_price = order.executed.price
            elif order.issell():
                self.entry_price = None
                self.stop_price = None
                self.highest_price = None

    def next(self):
        close = float(self.data.close[0])

        if np.isnan(self.atr[0]) or self.atr[0] <= 0:
            return

        atr = float(self.atr[0])

        # Update trailing information
        if self.position:
            self.highest_price = max(self.highest_price, close)

            # Hard stop based on ATR from entry
            hard_stop = self.entry_price - self.p.atr_stop_mult * atr

            # Trailing stop based on highest price reached
            trailing_stop = self.highest_price - self.p.atr_trail_mult * atr

            active_stop = max(hard_stop, trailing_stop)

            # Exit rules
            if close < active_stop:
                self.close()
                return

            if self.signal[0] == 0:
                self.close()
                return

            if close < self.sma50[0]:
                self.close()
                return

        else:
            # Entry rules
            if self.signal[0] == 1 and self.ml_prob[0] >= self.p.min_prob and close > self.sma200[0]:
                cash = self.broker.getcash()
                portfolio_value = self.broker.getvalue()

                # Risk sizing based on ATR stop distance
                stop_distance = self.p.atr_stop_mult * atr
                if stop_distance <= 0:
                    return

                risk_amount = portfolio_value * self.p.risk_per_trade
                size_risk = int(risk_amount / stop_distance)

                # Cash cap
                max_cash_to_use = cash * self.p.max_allocation
                size_cash = int(max_cash_to_use / close)

                size = min(size_risk, size_cash)

                if size > 0:
                    self.buy(size=size)


# -----------------------------
# BENCHMARK STRATEGY
# -----------------------------
class BuyAndHoldStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            size = int(self.broker.getcash() / self.data.close[0])
            if size > 0:
                self.buy(size=size)


# -----------------------------
# BACKTEST RUNNER
# -----------------------------
def run_backtest(test_df):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(ImprovedMLStrategy)
    cerebro.broker.setcash(INITIAL_CASH)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%

    data_feed = MLDataFeed(dataname=test_df)
    cerebro.adddata(data_feed)

    # analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

    results = cerebro.run()
    strat = results[0]

    final_value = cerebro.broker.getvalue()
    total_return = (final_value / INITIAL_CASH - 1) * 100

    sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
    drawdown = strat.analyzers.drawdown.get_analysis()
    max_dd = drawdown.max.drawdown if hasattr(drawdown, "max") else None
    trades = strat.analyzers.trades.get_analysis()

    return {
        "final_value": final_value,
        "return_pct": total_return,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "trades": trades,
    }


def run_buy_and_hold(test_df):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BuyAndHoldStrategy)
    cerebro.broker.setcash(INITIAL_CASH)
    cerebro.broker.setcommission(commission=0.001)

    data_feed = bt.feeds.PandasData(dataname=test_df)
    cerebro.adddata(data_feed)

    cerebro.run()
    final_value = cerebro.broker.getvalue()
    total_return = (final_value / INITIAL_CASH - 1) * 100
    return total_return


def summarize_trade_analyzer(trades):
    total_closed = trades.get("total", {}).get("closed", 0)
    total_open = trades.get("total", {}).get("open", 0)
    won = trades.get("won", {}).get("total", 0)
    lost = trades.get("lost", {}).get("total", 0)

    pnl_net = trades.get("pnl", {}).get("net", {})
    avg_pnl = pnl_net.get("average", None)
    total_pnl = pnl_net.get("total", None)

    return {
        "closed": total_closed,
        "open": total_open,
        "won": won,
        "lost": lost,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
    }


# -----------------------------
# MAIN
# -----------------------------
print("Building cross-sectional training set...")
train_df, feature_cols = build_training_set(UNIVERSE, TRAIN_START, TRAIN_END)
print(f"Training rows: {len(train_df):,}")
print(f"Features: {feature_cols}")

print("\nTraining model...")
model, scaler = train_model(train_df, feature_cols)

# Feature importance report
importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
print("\nTop feature importances:")
print(importances.head(10).round(4).to_string())

results = {}

print("\n" + "=" * 100)
print("OUT-OF-SAMPLE TEST (2023)")
print("=" * 100)

for ticker in UNIVERSE:
    try:
       # pull earlier data so indicators have warmup history
        test_download_start = "2022-01-01"
        raw_test = download_data(ticker, test_download_start, TEST_END)

        if raw_test.empty:
            print(f"Skipping {ticker}: no test data")
            continue

        feat_test, _ = create_features(raw_test)

        # now slice to actual out-of-sample window
        feat_test = feat_test.loc[feat_test.index >= TEST_START].copy()
        raw_test_2023 = raw_test.loc[raw_test.index >= TEST_START].copy()

        if len(feat_test) < 20:
            print(f"Skipping {ticker}: not enough usable 2023 rows after warmup")
            continue

        pred_test = add_predictions(feat_test, model, scaler, feature_cols, prob_threshold=0.55)

        ml_stats = run_backtest(pred_test)
        bh_return = run_buy_and_hold(raw_test_2023)

        trade_summary = summarize_trade_analyzer(ml_stats["trades"])

        results[ticker] = {
            "ml_return": ml_stats["return_pct"],
            "bh_return": bh_return,
            "diff": ml_stats["return_pct"] - bh_return,
            "sharpe": ml_stats["sharpe"],
            "max_dd": ml_stats["max_dd"],
            "closed_trades": trade_summary["closed"],
            "won": trade_summary["won"],
            "lost": trade_summary["lost"],
        }

        print(
            f"{ticker:<6} | ML {ml_stats['return_pct']:>7.2f}% | "
            f"BH {bh_return:>7.2f}% | "
            f"Diff {ml_stats['return_pct'] - bh_return:>7.2f}% | "
            f"Sharpe {str(round(ml_stats['sharpe'], 2)) if ml_stats['sharpe'] is not None else 'N/A':>5} | "
            f"MaxDD {round(ml_stats['max_dd'], 2) if ml_stats['max_dd'] is not None else 'N/A':>6} | "
            f"Trades {trade_summary['closed']}"
        )

    except Exception as e:
        print(f"{ticker}: ERROR -> {e}")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

if results:
    summary = pd.DataFrame(results).T.sort_values("diff", ascending=False)
    print(summary.round(2).to_string())

    wins = int((summary["diff"] > 0).sum())
    print(f"\nML beats buy & hold on {wins}/{len(summary)} symbols")
else:
    print("No valid results generated.")

print("\n=== TEST COMPLETE ===")