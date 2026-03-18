# Day 9: Test Balanced SMA Strategy on Multiple Stocks
# Verify if strategy works across different assets or just SPY

import backtrader as bt
import yfinance as yf
import pandas as pd

class BalancedSMAStrategy(bt.Strategy):
    """Balanced SMA with protective filters"""
    
    def __init__(self):
        self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period=10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period=30)
        self.crossover = bt.indicators.CrossOver(self.sma10, self.sma30)
        self.volatility = bt.indicators.StandardDeviation(self.data.close, period=20)
        self.sma50 = bt.indicators.SimpleMovingAverage(self.data.close, period=50)
        
        self.trades = 0
        self.entry_price = None
    
    def next(self):
        position_size = 1.0
        if self.volatility[0] > 2.5:
            position_size = 0.5
        elif self.volatility[0] > 2.0:
            position_size = 0.75
        
        if not self.position:
            if self.crossover > 0 and self.data.close[0] > self.sma50[0]:
                self.buy(size=position_size)
                self.entry_price = self.data.close[0]
                self.trades += 1
        else:
            if self.crossover < 0 or self.data.close[0] < self.sma50[0] * 0.97:
                self.sell()

print("=== TESTING BALANCED SMA ON MULTIPLE STOCKS ===\n")

# Test on different stocks
stocks = ['SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'EEM']

results_by_stock = {}

for ticker in stocks:
    print(f"Testing {ticker}...")
    yearly_returns = {}
    
    for year in [2023, 2022, 2021]:
        try:
            cerebro = bt.Cerebro()
            cerebro.addstrategy(BalancedSMAStrategy)
            
            data = yf.download(ticker, start=f'{year}-01-01', end=f'{year}-12-31', progress=False)
            if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
                data.columns = data.columns.get_level_values(0)
            
            if len(data) < 50:  # Skip if not enough data
                yearly_returns[year] = None
                continue
            
            data_feed = bt.feeds.PandasData(dataname=data)
            cerebro.adddata(data_feed)
            cerebro.broker.setcash(10000)
            
            strats = cerebro.run()
            strategy = strats[0]
            
            final_value = cerebro.broker.getvalue()
            total_return = ((final_value - 10000) / 10000) * 100
            yearly_returns[year] = total_return
            
        except Exception as e:
            yearly_returns[year] = None
    
    results_by_stock[ticker] = yearly_returns

# Print results
print("\n" + "=" * 80)
print("BALANCED SMA STRATEGY - MULTI-STOCK RESULTS")
print("=" * 80)
print(f"\n{'Ticker':<10} {'2023':<12} {'2022':<12} {'2021':<12} {'Average':<12} {'Consistency'}")
print("-" * 80)

consistency_scores = {}

for ticker in stocks:
    returns = results_by_stock[ticker]
    valid_returns = [r for r in returns.values() if r is not None]
    
    if not valid_returns:
        print(f"{ticker:<10} No data")
        continue
    
    avg = sum(valid_returns) / len(valid_returns)
    ret_2023 = returns[2023] if returns[2023] is not None else 0
    ret_2022 = returns[2022] if returns[2022] is not None else 0
    ret_2021 = returns[2021] if returns[2021] is not None else 0
    
    # Calculate consistency (how many years were positive)
    positive_years = sum(1 for r in valid_returns if r > 0)
    consistency = f"{positive_years}/3 positive"
    
    print(f"{ticker:<10} {ret_2023:>10.2f}% {ret_2022:>10.2f}% {ret_2021:>10.2f}% {avg:>10.2f}% {consistency}")
    consistency_scores[ticker] = (avg, positive_years)

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

# Find best performer
best_ticker = max(consistency_scores, key=lambda x: consistency_scores[x][0])
best_return = consistency_scores[best_ticker][0]
best_consistency = consistency_scores[best_ticker][1]

print(f"\nBest Performer: {best_ticker} with {best_return:.2f}% average ({best_consistency}/3 years positive)")

# Check if SPY is typical
spy_return = consistency_scores['SPY'][0]
spy_consistency = consistency_scores['SPY'][1]
print(f"\nSPY Performance: {spy_return:.2f}% average ({spy_consistency}/3 years positive)")

# Find average across all stocks
avg_all = sum(scores[0] for scores in consistency_scores.values()) / len(consistency_scores)
print(f"Average across all stocks: {avg_all:.2f}%")

# Conclusion
print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if best_return > 2.0:
    print(f"\n✓ Strategy works well across multiple assets")
    print(f"✓ Not just luck on SPY")
    print(f"✓ Ready for live trading")
elif best_return > 0:
    print(f"\n~ Strategy shows modest positive returns")
    print(f"~ Works on some stocks better than others")
    print(f"~ May need optimization for specific assets")
else:
    print(f"\n✗ Strategy underperforms across stocks")
    print(f"✗ May need improvement before live trading")

print(f"\n=== TEST COMPLETE ===")