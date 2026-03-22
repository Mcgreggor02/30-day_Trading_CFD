# Day 11: Analyze ML Performance by Asset
# Why does ML win on some stocks but lose on others?

import yfinance as yf
import numpy as np
import pandas as pd

print("=== ANALYZING ML PERFORMANCE DIFFERENCES ===\n")

# Day 10 Results
results = {
    'SPY': {'ml': 29.03, 'bh': 23.85, 'winner': 'ML', 'diff': 5.18},
    'EEM': {'ml': 13.32, 'bh': -1.03, 'winner': 'ML', 'diff': 14.35},
    'TLT': {'ml': -0.39, 'bh': -3.00, 'winner': 'ML', 'diff': 2.61},
    'QQQ': {'ml': 19.33, 'bh': 52.77, 'winner': 'BH', 'diff': -33.44},
    'IWM': {'ml': 3.04, 'bh': 14.77, 'winner': 'BH', 'diff': -11.74},
    'GLD': {'ml': 1.46, 'bh': 11.50, 'winner': 'BH', 'diff': -10.04},
}

print("PERFORMANCE SUMMARY:")
print(f"{'Stock':<10} {'ML Return':<15} {'B&H Return':<15} {'Winner':<12} {'Gap'}")
print("-" * 65)

for ticker, data in results.items():
    print(f"{ticker:<10} {data['ml']:>13.2f}% {data['bh']:>13.2f}% {data['winner']:<12} {data['diff']:>+.2f}%")

# Analyze market characteristics
print("\n" + "="*65)
print("MARKET CHARACTERISTICS IN 2023")
print("="*65)

stocks = ['SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'EEM']

for ticker in stocks:
    data = yf.download(ticker, start='2023-01-01', end='2023-12-31', progress=False)
    if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
                     data.columns = data.columns.get_level_values(0) 
    # Calculate metrics
    returns = data['Close'].pct_change() * 100
    volatility = returns.std()
    trend = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0] * 100
    max_drawdown = ((data['Close'].cummin() - data['Close']) / data['Close'].cummin()).min() * 100
    
    print(f"\n{ticker}:")
    print(f"  Volatility: {volatility:.2f}%")
    print(f"  Trend: {trend:+.2f}%")
    print(f"  Max Drawdown: {max_drawdown:.2f}%")

# Analysis
print("\n" + "="*65)
print("WHY ML WINS ON SPY/EEM/TLT BUT LOSES ON QQQ/IWM/GLD")
print("="*65)

print("""
ML WINS ON:
- SPY: Large cap, stable, predictable patterns → ML finds edge
- EEM: Volatile, mean-reverting, clear corrections → ML exploits bounces
- TLT: Bonds, consistent patterns, trending → ML predicts direction well

ML LOSES ON:
- QQQ: Tech heavy, massive rallies, momentum dominates
  Problem: ML tries to time peaks, misses the rally
- IWM: Small cap, choppy, unpredictable, low liquidity
  Problem: ML signals noise, not real trends
- GLD: Commodity, external shocks, no clear patterns
  Problem: ML has no edge in gold price movements

SOLUTION:
Create STOCK-SPECIFIC models!
- Train separate RF model for SPY data
- Train separate RF model for QQQ data
- Each learns the patterns for THAT asset
- This is what professional quant firms do!
""")

print("\n=== SESSION 1 ANALYSIS COMPLETE ===")