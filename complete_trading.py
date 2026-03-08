# Day 3: Complete Trading System
# Combines volatility (risk) + momentum (trend) for trading signals

import numpy as np
import yfinance as yf

print("Building complete trading system...\n")

# Download data
spy_data = yf.download('LMT', period='3mo', progress=False)

# Calculate returns and volatility
returns = spy_data['Close'].pct_change() * 100
volatility = np.std(returns)
avg_return = np.mean(returns)

# Calculate momentum
momentum_period = 10
spy_data['Momentum'] = spy_data['Close'] - spy_data['Close'].shift(momentum_period)
spy_data['Momentum_Pct'] = (spy_data['Momentum'] / spy_data['Close'].squeeze().shift(momentum_period)) * 100

# Create complete trading signal
def generate_trading_signal(momentum, volatility, avg_return):
    """
    Generate signal based on BOTH momentum AND risk (volatility)
    """
    if volatility > 2.5:  # High volatility = high risk
        return "REDUCE_RISK"  # Take smaller positions
    elif momentum > 2 and volatility < 2.5:  # Strong uptrend + low risk
        return "BUY"
    elif momentum < -2 and volatility < 2.5:  # Strong downtrend + low risk
        return "SELL"
    else:
        return "HOLD"

# Generate signals for all days
signals = []
for momentum in spy_data['Momentum_Pct']:
    signal = generate_trading_signal(momentum, volatility, avg_return)
    signals.append(signal)

spy_data['Trading_Signal'] = signals

print("=== COMPLETE TRADING SYSTEM ===\n")
print(f"Market Volatility: {volatility:.3f}%")
print(f"Average Daily Return: {avg_return:.3f}%")
print(f"Risk Level: {'HIGH' if volatility > 2.5 else 'MODERATE' if volatility > 1.5 else 'LOW'}")

print(f"\n--- RECENT SIGNALS (Last 10 Days) ---")
print(spy_data[['Close', 'Momentum_Pct', 'Trading_Signal']].tail(10))

# Count signals
buy_count = (spy_data['Trading_Signal'] == 'BUY').sum()
sell_count = (spy_data['Trading_Signal'] == 'SELL').sum()
hold_count = (spy_data['Trading_Signal'] == 'HOLD').sum()
reduce_count = (spy_data['Trading_Signal'] == 'REDUCE_RISK').sum()

print(f"\n--- SIGNAL DISTRIBUTION ---")
print(f"BUY: {buy_count}")
print(f"SELL: {sell_count}")
print(f"HOLD: {hold_count}")
print(f"REDUCE_RISK: {reduce_count}")

print(f"\n--- KEY INSIGHT ---")
print(f"This system doesn't just look for trends (momentum).")
print(f"It also considers RISK (volatility).")
print(f"Great traders manage risk FIRST, chase returns SECOND.")