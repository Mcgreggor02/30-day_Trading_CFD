# Day 9: Market Regime Detector
# Identifies bull, bear, or sideways market conditions
# Used to switch between aggressive and defensive strategies

import backtrader as bt
import yfinance as yf
import numpy as np

print("=== MARKET REGIME DETECTOR ===\n")

# Download data
data = yf.download('SPY', start='2020-01-01', end='2023-12-31', progress=False)

if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
        data.columns = data.columns.get_level_values(0)

# Calculate regime indicators
close = data['Close'].values
sma50 = data['Close'].rolling(50).mean().values
sma200 = data['Close'].rolling(200).mean().values

# Calculate returns
returns = np.diff(close) / close[:-1]
volatility = np.std(returns[-252:]) if len(returns) >= 252 else 0  # Last year volatility

print(f"Current Market Data:")
print(f"Price: ${close[-1]:.2f}")
print(f"SMA50: ${sma50[-1]:.2f}")
print(f"SMA200: ${sma200[-1]:.2f}")
print(f"Volatility (1-year): {volatility*100:.2f}%")

# Define regime detection rules
def detect_regime(price, sma50, sma200, volatility):
    """
    Detect market regime based on price position and trend
    
    BULL: Price above both SMA50 and SMA200 (strong uptrend)
    BEAR: Price below both SMA50 and SMA200 (strong downtrend)
    SIDEWAYS: Price between the moving averages (choppy, no clear direction)
    """
    
    if price > sma50 and price > sma200 and sma50 > sma200:
        return "BULL"
    elif price < sma50 and price < sma200 and sma50 < sma200:
        return "BEAR"
    else:
        return "SIDEWAYS"

# Test regime detection on historical data
print(f"\n=== REGIME DETECTION OVER TIME ===\n")

regimes = []
dates = data.index[200:]  # Start after SMA200 stabilizes

for i in range(200, len(close)):
    regime = detect_regime(close[i], sma50[i], sma200[i], volatility)
    regimes.append(regime)

# Count regime occurrences
regime_counts = {'BULL': 0, 'BEAR': 0, 'SIDEWAYS': 0}
for regime in regimes:
    regime_counts[regime] += 1

print(f"Regime Distribution (2020-2023):")
print(f"BULL:     {regime_counts['BULL']:4d} days ({regime_counts['BULL']/len(regimes)*100:5.1f}%)")
print(f"BEAR:     {regime_counts['BEAR']:4d} days ({regime_counts['BEAR']/len(regimes)*100:5.1f}%)")
print(f"SIDEWAYS: {regime_counts['SIDEWAYS']:4d} days ({regime_counts['SIDEWAYS']/len(regimes)*100:5.1f}%)")

# Show regime for each year
print(f"\n=== REGIME BY YEAR ===\n")

years = ['2023', '2022', '2021', '2020']
for year in years:
    year_start = f'{year}-01-01'
    year_end = f'{year}-12-31'
    
    year_data = data[year_start:year_end]
    year_close = year_data['Close'].values
    year_sma50 = year_data['Close'].rolling(50).mean().values
    year_sma200 = year_data['Close'].rolling(200).mean().values
    
    # Get predominant regime
    year_regimes = []
    for i in range(len(year_close)):
        if not np.isnan(year_sma50[i]) and not np.isnan(year_sma200[i]):
            regime = detect_regime(year_close[i], year_sma50[i], year_sma200[i], volatility)
            year_regimes.append(regime)
    
    if year_regimes:
        most_common = max(set(year_regimes), key=year_regimes.count)
        bull_pct = year_regimes.count('BULL') / len(year_regimes) * 100
        bear_pct = year_regimes.count('BEAR') / len(year_regimes) * 100
        side_pct = year_regimes.count('SIDEWAYS') / len(year_regimes) * 100
        
        print(f"{year}: {most_common:10s} (Bull: {bull_pct:5.1f}%, Bear: {bear_pct:5.1f}%, Sideways: {side_pct:5.1f}%)")

print(f"\n=== SESSION 1 COMPLETE ===")
print(f"Market regime detector created and tested")
print(f"Ready to implement strategy switching in Session 2")