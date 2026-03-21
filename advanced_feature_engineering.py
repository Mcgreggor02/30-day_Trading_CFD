# Day 10: Advanced Feature Engineering for ML
# Create rich feature set that captures market patterns
# Better features = better predictions

import numpy as np
import pandas as pd
import yfinance as yf

print("=== ADVANCED FEATURE ENGINEERING ===\n")

# Download sample data
data = yf.download('SPY', start='2023-01-01', end='2023-12-31', progress=False)
if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
                    data.columns = data.columns.get_level_values(0)

print(f"Creating advanced features from {len(data)} trading days...\n")

df = data.copy()

# ========== PRICE-BASED FEATURES ==========
print("1. PRICE-BASED FEATURES")
df['returns_1d'] = df['Close'].pct_change() * 100
df['returns_5d'] = df['Close'].pct_change(5) * 100
df['returns_10d'] = df['Close'].pct_change(10) * 100
df['high_low_ratio'] = (df['High'] - df['Low']) / df['Close'] * 100
df['close_open_ratio'] = (df['Close'] - df['Open']) / df['Close'] * 100
df['price_range'] = (df['High'] - df['Low']) / df['Close']
print("   ✓ Price momentum (1d, 5d, 10d)")
print("   ✓ Intraday volatility (high-low)")
print("   ✓ Open-close relationship")

# ========== MOVING AVERAGE FEATURES ==========
print("\n2. MOVING AVERAGE FEATURES")
for period in [5, 10, 20, 50]:
    df[f'sma{period}'] = df['Close'].rolling(period).mean()
    df[f'close_above_sma{period}'] = (df['Close'] > df[f'sma{period}']).astype(int)

df['sma_slope_10'] = df['sma10'].diff()
df['sma_slope_20'] = df['sma20'].diff()
print("   ✓ SMA levels (5, 10, 20, 50)")
print("   ✓ Price vs SMA relationships")
print("   ✓ SMA slope (momentum of moving average)")

# ========== VOLATILITY FEATURES ==========
print("\n3. VOLATILITY FEATURES")
df['volatility_10'] = df['returns_1d'].rolling(10).std()
df['volatility_20'] = df['returns_1d'].rolling(20).std()
df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
df['atr_percent'] = df['atr'] / df['Close'] * 100
print("   ✓ Rolling volatility (10d, 20d)")
print("   ✓ Average True Range (ATR)")

# ========== MOMENTUM FEATURES ==========
print("\n4. MOMENTUM FEATURES")
df['roc_5'] = (df['Close'] - df['Close'].shift(5)) / df['Close'].shift(5) * 100
df['roc_10'] = (df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10) * 100
df['momentum_5'] = df['Close'].diff(5)
df['momentum_10'] = df['Close'].diff(10)
print("   ✓ Rate of Change (ROC) 5d, 10d")
print("   ✓ Raw momentum")

# ========== RSI (RELATIVE STRENGTH INDEX) ==========
print("\n5. RSI (OVERBOUGHT/OVERSOLD)")
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))
print("   ✓ RSI indicator")

# ========== VOLUME-BASED FEATURES ==========
print("\n6. VOLUME FEATURES")
if 'Volume' in df.columns:
    df['volume_ma'] = df['Volume'].rolling(20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_ma']
    print("   ✓ Volume moving average")
    print("   ✓ Volume ratio (above/below average)")

# ========== TREND FEATURES ==========
print("\n7. TREND FEATURES")
df['higher_high'] = (df['High'] > df['High'].shift(1)).astype(int)
df['higher_low'] = (df['Low'] > df['Low'].shift(1)).astype(int)
df['lower_high'] = (df['High'] < df['High'].shift(1)).astype(int)
df['lower_low'] = (df['Low'] < df['Low'].shift(1)).astype(int)
print("   ✓ Higher Highs/Lows (uptrend)")
print("   ✓ Lower Highs/Lows (downtrend)")

# ========== MEAN REVERSION FEATURES ==========
print("\n8. MEAN REVERSION FEATURES")
df['distance_from_ma'] = (df['Close'] - df['sma20']) / df['sma20'] * 100
df['zscore'] = (df['Close'] - df['sma20']) / df['volatility_20']
print("   ✓ Distance from 20-day MA")
print("   ✓ Z-score (how far from mean)")

# ========== TARGET VARIABLE ==========
print("\n9. TARGET VARIABLE")
df['target_1d'] = (df['returns_1d'].shift(-1) > 0).astype(int)
df['target_5d'] = (df['returns_5d'].shift(-1) > 0).astype(int)
print("   ✓ Next day price up/down")
print("   ✓ Next 5 days price up/down")

# Remove NaN
df = df.dropna()

# Summary
print(f"\n{'='*60}")
print("FEATURE SUMMARY")
print(f"{'='*60}")
print(f"Total features created: {len(df.columns) - 6}")  # -6 for OHLCV + Date
print(f"Rows available: {len(df)}")
print(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")

# Show sample features
print(f"\n{'='*60}")
print("SAMPLE DATA (first 5 rows)")
print(f"{'='*60}")

feature_cols = [col for col in df.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
print(df[feature_cols].head())

# Feature statistics
print(f"\n{'='*60}")
print("FEATURE STATISTICS")
print(f"{'='*60}")
print(df[feature_cols].describe())

# Save features
df.to_csv('advanced_features.csv')
print(f"\nFeatures saved to: advanced_features.csv")

print(f"\n=== SESSION 1 COMPLETE ===")
print(f"Advanced features ready for ML models")