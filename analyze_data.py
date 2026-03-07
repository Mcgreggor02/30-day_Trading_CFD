# Day 2 : Analyze Market Data with Pandas 
# This uses Pandas to calculate trading statistics 

import yfinance as yf
import pandas as pd 

#Download SPY data 

print("Downloading Spy data for analysis...")
spy_data = yf.download('ASTS', period='3mo', progress=False)

#Calculate daily returns 
spy_data['Daily_Return'] = spy_data['Close'].pct_change() * 100

# Calculate moving averages 
spy_data['MA_20'] = spy_data['Close'].rolling(window=20).mean()
spy_data['MA_50'] = spy_data['Close'].rolling(window=50).mean()

print("\n SPY ANALYSIS (3 Months) ===\n")
print(spy_data[['Close','Daily_Return', 'MA_20', 'MA_50' ]].tail(10))

print(f"\n--- STATISTICS ---")
print(f"Average Daily Return: {spy_data['Daily_Return'].mean():.3f}%")
print(f"Daily Return Std Dev: {spy_data['Daily_Return'].std():.3f}%")
print(f"Max Daily Return: {spy_data['Daily_Return'].max():.3f}%")
print(f"Min Daily Return: {spy_data['Daily_Return'].min():.3f}%")

# Count positive vs negative days
positive_days = (spy_data['Daily_Return'] > 0).sum()
negative_days = (spy_data['Daily_Return'] < 0).sum()
total_days = positive_days + negative_days

print(f"\n--- TRADING DAYS ---")
print(f"Positive Days: {positive_days} ({(positive_days/total_days)*100:.1f}%)")
print(f"Negative Days: {negative_days} ({(negative_days/total_days)*100:.1f}%)")
