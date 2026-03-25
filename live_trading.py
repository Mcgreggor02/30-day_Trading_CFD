# Day 12: Live Trading Engine
# Fetch today's data, generate signals, track performance

import yfinance as yf
import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
import json
import os

print("=== LIVE TRADING ENGINE ===\n")

# Load trained models
with open("ensemble_models.pkl", "rb") as f:
    models = pickle.load(f)

rf_model = models["rf_model"]
scaler = models["scaler"]
feature_cols = models["feature_cols"]


def get_latest_data(ticker, days=60):
    """Fetch latest market data"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if data is None or data.empty:
            return None

        # Flatten MultiIndex columns if yfinance returns them
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Keep only expected OHLCV columns if present
        expected_cols = ["Open", "High", "Low", "Close", "Volume"]
        existing_cols = [col for col in expected_cols if col in data.columns]
        data = data[existing_cols].copy()

        # Drop rows with missing price data
        data = data.dropna(subset=[c for c in ["Open", "High", "Low", "Close"] if c in data.columns])

        if data.empty:
            return None

        return data

    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        return None


def to_1d_float_array(x):
    """Convert pandas Series/DataFrame/array into a flat float numpy array"""
    return np.asarray(x, dtype=float).reshape(-1)


def calculate_features(data):
    """Calculate ML features from OHLCV data"""
    df = data.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    close = to_1d_float_array(df["Close"])
    high = to_1d_float_array(df["High"])
    low = to_1d_float_array(df["Low"])
    open_ = to_1d_float_array(df["Open"])
    volume = to_1d_float_array(df["Volume"])

    if len(close) < 20:
        raise ValueError("Not enough data to calculate features (need at least 20 rows)")

    # Returns
    returns_1d = (close[-1] - close[-2]) / close[-2] * 100 if len(close) >= 2 and close[-2] != 0 else 0
    returns_5d = (close[-1] - close[-6]) / close[-6] * 100 if len(close) >= 6 and close[-6] != 0 else 0
    returns_10d = (close[-1] - close[-11]) / close[-11] * 100 if len(close) >= 11 and close[-11] != 0 else 0

    # Price structure
    high_low = (high[-1] - low[-1]) / close[-1] * 100 if close[-1] != 0 else 0
    close_open = (close[-1] - open_[-1]) / close[-1] * 100 if close[-1] != 0 else 0
    price_range = (high[-1] - low[-1]) / close[-1] if close[-1] != 0 else 0

    # Moving averages
    sma5 = np.mean(close[-5:]) if len(close) >= 5 else np.mean(close)
    sma10 = np.mean(close[-10:]) if len(close) >= 10 else np.mean(close)
    sma20 = np.mean(close[-20:]) if len(close) >= 20 else np.mean(close)
    sma50 = np.mean(close[-50:]) if len(close) >= 50 else np.mean(close)

    c_above_5 = 1 if close[-1] > sma5 else 0
    c_above_10 = 1 if close[-1] > sma10 else 0
    c_above_20 = 1 if close[-1] > sma20 else 0
    c_above_50 = 1 if close[-1] > sma50 else 0

    # Slope of SMA relative to previous SMA window
    prev_sma10 = np.mean(close[-11:-1]) if len(close) >= 11 else sma10
    prev_sma20 = np.mean(close[-21:-1]) if len(close) >= 21 else sma20

    sma_slope_10 = (sma10 - prev_sma10) / prev_sma10 * 100 if prev_sma10 != 0 else 0
    sma_slope_20 = (sma20 - prev_sma20) / prev_sma20 * 100 if prev_sma20 != 0 else 0

    # Volatility
    vol_returns = np.diff(close) / close[:-1] * 100 if len(close) >= 2 else np.array([0.0])
    vol_10 = np.std(vol_returns[-10:]) if len(vol_returns) >= 10 else np.std(vol_returns) if len(vol_returns) > 0 else 0
    vol_20 = np.std(vol_returns[-20:]) if len(vol_returns) >= 20 else np.std(vol_returns) if len(vol_returns) > 0 else 0

    # ATR (simple version)
    atr = np.mean(high[-14:] - low[-14:]) if len(high) >= 14 else np.mean(high - low)
    atr_pct = atr / close[-1] * 100 if close[-1] != 0 else 0

    # ROC
    roc_5 = (close[-1] - close[-6]) / close[-6] * 100 if len(close) >= 6 and close[-6] != 0 else 0
    roc_10 = (close[-1] - close[-11]) / close[-11] * 100 if len(close) >= 11 and close[-11] != 0 else 0

    # Momentum
    mom_5 = close[-1] - close[-6] if len(close) >= 6 else 0
    mom_10 = close[-1] - close[-11] if len(close) >= 11 else 0

    # RSI (simple rolling-free version)
    delta = np.diff(close)
    if len(delta) == 0:
        rsi = 50
    else:
        gains = delta[delta > 0]
        losses = -delta[delta < 0]

        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0

        if avg_loss == 0:
            rsi = 100 if avg_gain > 0 else 50
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

    # Volume
    vol_window = volume[-20:] if len(volume) >= 20 else volume
    vol_ma = np.mean(vol_window) if len(vol_window) > 0 and np.all(np.isfinite(vol_window)) else 1
    vol_ratio = volume[-1] / vol_ma if vol_ma > 0 else 1

    # Trend
    h_high = 1 if len(high) >= 2 and high[-1] > high[-2] else 0
    h_low = 1 if len(low) >= 2 and low[-1] > low[-2] else 0
    l_high = 1 if len(high) >= 2 and high[-1] < high[-2] else 0
    l_low = 1 if len(low) >= 2 and low[-1] < low[-2] else 0

    # Mean reversion
    dist_ma = (close[-1] - sma20) / sma20 * 100 if sma20 != 0 else 0
    zscore = dist_ma / vol_20 if vol_20 > 0 else 0

    # Build feature dict
    features = {
        "High": high[-1],
        "Low": low[-1],
        "Open": open_[-1],
        "Volume": volume[-1],
        "returns_1d": returns_1d,
        "returns_5d": returns_5d,
        "returns_10d": returns_10d,
        "high_low_ratio": high_low,
        "close_open_ratio": close_open,
        "price_range": price_range,
        "sma5": sma5,
        "close_above_sma5": c_above_5,
        "sma10": sma10,
        "close_above_sma10": c_above_10,
        "sma20": sma20,
        "close_above_sma20": c_above_20,
        "sma50": sma50,
        "close_above_sma50": c_above_50,
        "sma_slope_10": sma_slope_10,
        "sma_slope_20": sma_slope_20,
        "volatility_10": vol_10,
        "volatility_20": vol_20,
        "atr": atr,
        "atr_percent": atr_pct,
        "roc_5": roc_5,
        "roc_10": roc_10,
        "momentum_5": mom_5,
        "momentum_10": mom_10,
        "rsi": rsi,
        "volume_ma": vol_ma,
        "volume_ratio": vol_ratio,
        "higher_high": h_high,
        "higher_low": h_low,
        "lower_high": l_high,
        "lower_low": l_low,
        "distance_from_ma": dist_ma,
        "zscore": zscore,
    }

    return features, close[-1]


def generate_signal(ticker):
    """Generate trading signal for today"""
    print(f"\n{ticker}:")
    print("-" * 50)

    # Get data
    data = get_latest_data(ticker, days=60)
    if data is None or len(data) < 20:
        print("  Not enough data")
        return None

    try:
        # Calculate features
        features, current_price = calculate_features(data)

        # Validate model features
        missing_features = [col for col in feature_cols if col not in features]
        if missing_features:
            print(f"  Missing features for model: {missing_features}")
            return None

        # Build feature array
        feature_array = np.array([features[col] for col in feature_cols], dtype=float).reshape(1, -1)

        # Scale
        feature_scaled = scaler.transform(feature_array)

        # Predict
        prob = rf_model.predict_proba(feature_scaled)[0][1]
        prediction = rf_model.predict(feature_scaled)[0]

        signal = "BUY" if prediction == 1 else "SELL"

        print(f"  Current Price: ${current_price:.2f}")
        print(f"  Prediction: {signal}")
        print(f"  Confidence: {prob:.1%}")
        print(f"  SMA20: ${features['sma20']:.2f}")
        print(f"  RSI: {features['rsi']:.0f}")
        print(f"  Volatility (20d): {features['volatility_20']:.2f}%")

        return {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "price": float(current_price),
            "signal": signal,
            "confidence": float(prob),
            "sma20": float(features["sma20"]),
            "rsi": float(features["rsi"]),
            "volatility": float(features["volatility_20"]),
        }

    except Exception as e:
        print(f"  Error generating signal: {e}")
        return None


# Generate signals for major stocks
print("GENERATING TODAY'S TRADING SIGNALS\n")
print("=" * 50)

stocks = ["SPY", "QQQ", "EEM"]
signals = []

for ticker in stocks:
    signal = generate_signal(ticker)
    if signal:
        signals.append(signal)

# Save signals
with open("today_signals.json", "w") as f:
    json.dump(signals, f, indent=2)

print("\n" + "=" * 50)
print("SIGNALS SAVED TO: today_signals.json")
print("=" * 50)

print("\n=== SESSION 1 COMPLETE ===")
print("Live trading engine operational")
print("Ready for daily deployment")