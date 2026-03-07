#Day  2: Download Real Market Data
# This fetches actual stock prices from Yahoo Finance 

import yfinance as yf 

#Download SPY data for the last 30 days
print("Downloading SPY data...")
spy_data = yf.download('SPY', period='1mo', progress=False)

print("\n=== SPY DATA (Last 30 days) ===\n")
print(spy_data.head(10)) #Show first 10 rows

print(f"\n--- STATISTICS ---")
print(f"Latest Close Price: ${spy_data['Close'].iloc[-1].item():.2f}")
print(f"30-Day High: ${spy_data['High'].max().item():.2f}")
print(f"30-Day Low: ${spy_data['Low'].min().item():.2f}")
print(f"Average Close: ${spy_data['Close'].mean().item():.2f}")

# Calculate 30-day return 
start_price = spy_data['Close'].iloc[0].item()
end_price = spy_data['Close'].iloc[-1].item()
return_30d = ((end_price - start_price)/ start_price) * 100

print(f"30-Day Return: {return_30d:.2f}%")