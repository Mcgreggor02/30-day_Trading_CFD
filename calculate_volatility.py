#Day 3 Calculate Volatility (Standard Deviation of returns)
# Volatility = risk. High volatilty = bigger price swings 

#libraries 
import numpy as np 
import yfinance as yf

#Download real data 
print("Downloading SPY data...")
spy_data = yf.download('SPY', period="6mo", progress=False)


# Calculate daily returns 
returns = spy_data["Close"].pct_change().dropna().values * 100

#Calculate volatility (standard deviation of returns)
volatility = np.std(returns)
avg_return = np.mean(returns)

print("=== VOLATILITY ANALYSIS ===\n")
print(f"Period: 6 months of SPY data")
print(f"Average Daily return: {avg_return:.3f}%")
print(f"Volatility (Std Dev): {volatility:.3f}%")
print(f"Annualized Volatilty: {volatility * np.sqrt(252):.2f}% ") #252 as it is the total trading years 

#Calculate Sharpe Ratio (return per unit of risk)
# Assuming 0% risk-free rate 
sharpe_ratio = avg_return / volatility

print(f"\n--- RISK METRICS ---")
print(f"Sharpe Ratio: {sharpe_ratio:.3f}")
print(f"(Higher = better risk-adjusted returns)")

#Days within 1 std dev (normal distribution)
upper_bound = avg_return + volatility
lower_bound = avg_return - volatility

within_1std = ((returns >= lower_bound) & (returns <= upper_bound)).sum()
pct_within_1std = (within_1std/ len(returns)) * 100

print(f"\n--- NORMAL DISTRIBUTION ---")
print(f"Days within 1 std dev: {within_1std} ({pct_within_1std:.1f}%)")
print(f"Expected (normal): ~68%")