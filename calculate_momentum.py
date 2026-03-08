#Day 3: Calculate Momentum Indicator 
# Momentum = rate of price change (how fast prices are moving)

import numpy as np 
import yfinance as yf

# Download real data 
print("Downloading SPY data...")
spy_data = yf.download("SPY", period="3mo", progress=False)

#Calculate momentum (rate of price change over 10 days)
momentum_period = 10
spy_data['Momentum'] = spy_data['Close'] - spy_data['Close'].shift(momentum_period)

#Calculate momentum percentage
spy_data['Momentum_Pct'] = (spy_data['Momentum']/ spy_data['Close'].squeeze().shift(momentum_period)) * 100

print(' === MOMENTUM ANALYSIS ===\n')
print(spy_data[['Close','Momentum', 'Momentum_Pct']].tail(10))

#Create momentum signals
spy_data['Signal'] = 'HOLD'
spy_data.loc[spy_data['Momentum_Pct'] >2, 'Signal'] = 'BUY' #Strong upward momentum
spy_data.loc[spy_data['Momentum_Pct'] < -2, 'Signal'] = 'SELL' #Strong downward momentum

print(f'\n === MOMENTUM SIGNALS (Last 10 Days) ===')
print(spy_data[['Close', 'Momentum_Pct', 'Signal']].tail(10))

#Count signals

buy_signals = (spy_data['Signal'] == 'BUY').sum()
sell_signals = (spy_data['Signal'] == 'SELL').sum()
hold_signals = (spy_data['Signal'] == 'HOLD').sum()


print(f"\n--- SIGNAL DISTRIBUTION ---")
print(f"BUY Signals: {buy_signals}")
print(f"SELL Signals: {sell_signals}")
print(f"HOLD Signals: {hold_signals}")