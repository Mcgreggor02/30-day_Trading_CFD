# Day 11: Train Stock-Specific ML Models
# Separate model for each stock = better accuracy

import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pickle
import warnings
warnings.filterwarnings('ignore')

print("=== TRAINING STOCK-SPECIFIC ML MODELS ===\n")

def create_features(data):
    """Create feature set from OHLCV data"""
    df = data.copy()
    
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    open_ = df['Open'].values
    volume = df['Volume'].values
    
    df['returns_1d'] = df['Close'].pct_change() * 100
    df['returns_5d'] = df['Close'].pct_change(5) * 100
    df['returns_10d'] = df['Close'].pct_change(10) * 100
    
    df['high_low_ratio'] = (df['High'] - df['Low']) / df['Close'] * 100
    df['close_open_ratio'] = (df['Close'] - df['Open']) / df['Close'] * 100
    df['price_range'] = (df['High'] - df['Low']) / df['Close']
    
    df['sma5'] = df['Close'].rolling(5).mean()
    df['sma10'] = df['Close'].rolling(10).mean()
    df['sma20'] = df['Close'].rolling(20).mean()
    df['sma50'] = df['Close'].rolling(50).mean()
    
    df['close_above_sma5'] = (df['Close'] > df['sma5']).astype(int)
    df['close_above_sma10'] = (df['Close'] > df['sma10']).astype(int)
    df['close_above_sma20'] = (df['Close'] > df['sma20']).astype(int)
    df['close_above_sma50'] = (df['Close'] > df['sma50']).astype(int)
    
    df['sma_slope_10'] = df['sma10'].diff()
    df['sma_slope_20'] = df['sma20'].diff()
    
    df['volatility_10'] = df['returns_1d'].rolling(10).std()
    df['volatility_20'] = df['returns_1d'].rolling(20).std()
    
    df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
    df['atr_percent'] = df['atr'] / df['Close'] * 100
    
    df['roc_5'] = (df['Close'] - df['Close'].shift(5)) / df['Close'].shift(5) * 100
    df['roc_10'] = (df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10) * 100
    
    df['momentum_5'] = df['Close'].diff(5)
    df['momentum_10'] = df['Close'].diff(10)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['volume_ma'] = df['Volume'].rolling(20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_ma']
    
    df['higher_high'] = (df['High'] > df['High'].shift(1)).astype(int)
    df['higher_low'] = (df['Low'] > df['Low'].shift(1)).astype(int)
    df['lower_high'] = (df['High'] < df['High'].shift(1)).astype(int)
    df['lower_low'] = (df['Low'] < df['Low'].shift(1)).astype(int)
    
    df['distance_from_ma'] = (df['Close'] - df['sma20']) / df['sma20'] * 100
    df['zscore'] = (df['Close'] - df['sma20']) / df['volatility_20']
    
    # Target: next day up/down
    df['target'] = (df['returns_1d'].shift(-1) > 0).astype(int)
    
    df = df.dropna()
    return df

def train_model(ticker):
    """Train Random Forest for specific stock"""
    print(f"Training {ticker}...")
    
    # Download 2-year data (2021-2023)
    data = yf.download(ticker, start='2021-01-01', end='2023-12-31', progress=False)
    if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
                     data.columns = data.columns.get_level_values(0)  
    # Create features
    df = create_features(data)
    
    feature_cols = [col for col in df.columns if col not in ['Close', 'High', 'Low', 'Open', 'Volume', 'target']]
    X = df[feature_cols].values
    y = df['target'].values
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train
    model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    model.fit(X_train_scaled, y_train)
    
    accuracy = model.score(X_test_scaled, y_test)
    print(f"  ✓ {ticker} accuracy: {accuracy:.1%}")
    
    return model, scaler, feature_cols, accuracy

# Train models for best performers
tickers = ['SPY', 'QQQ', 'EEM']
models_dict = {}

for ticker in tickers:
    model, scaler, feature_cols, accuracy = train_model(ticker)
    models_dict[ticker] = {
        'model': model,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'accuracy': accuracy
    }

# Save all models
with open('stock_specific_models.pkl', 'wb') as f:
    pickle.dump(models_dict, f)

print(f"\n✓ All stock-specific models saved to: stock_specific_models.pkl")

print(f"\n=== SUMMARY ===")
for ticker in tickers:
    acc = models_dict[ticker]['accuracy']
    print(f"{ticker}: {acc:.1%} accuracy")

print(f"\n=== SESSION 2 COMPLETE ===")
print(f"Stock-specific models ready for deployment")