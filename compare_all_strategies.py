# Day 5: Compare All Strategies
# Side-by-side comparison of SMA, Mean Reversion, and Momentum

import backtrader as bt
import yfinance as yf
import pandas as pd

# Define all three strategies
class SMAStrategy(bt.Strategy):
    def __init__(self):
        self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period=10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period=30)
        self.crossover = bt.indicators.CrossOver(self.sma10, self.sma30)
        self.trades = 0
    
    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
                self.trades += 1
        else:
            if self.crossover < 0:
                self.sell()

class MeanReversionStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=20)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=20)
        self.lower_band = self.sma - (2 * self.std)
        self.trades = 0
    
    def next(self):
        if not self.position:
            if self.data.close[0] < self.lower_band[0]:
                self.buy()
                self.trades += 1
        else:
            if self.data.close[0] > self.sma[0]:
                self.sell()

class MomentumStrategy(bt.Strategy):
    def __init__(self):
        self.momentum = self.data.close - self.data.close(-10)
        self.momentum_pct = (self.momentum / self.data.close(-10)) * 100
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=20)
        self.trades = 0
    
    def next(self):
        if not self.position:
            if self.momentum_pct[0] > 1.5 and self.data.close[0] > self.sma[0]:
                self.buy()
                self.trades += 1
        else:
            if self.momentum_pct[0] < -1.5 or self.data.close[0] < self.sma[0]:
                self.sell()

# Download data once
print("Downloading SPY data for 2023...")
data = yf.download('SPY', start='2023-01-01', end='2023-12-31', progress=False)

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

strategies = [
    ('SMA(10,30)', SMAStrategy),
    ('Mean Reversion', MeanReversionStrategy),
    ('Momentum', MomentumStrategy)
]

results = []

print("\n=== TESTING ALL STRATEGIES ===\n")

for name, strategy_class in strategies:
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)
    
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000)
    
    strats = cerebro.run()
    strategy = strats[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = ((final_value - 10000) / 10000) * 100
    
    results.append({
        'Strategy': name,
        'Return': total_return,
        'Trades': strategy.trades,
        'Final Value': final_value
    })
    
    print(f"{name:20s}: {total_return:>7.2f}% return | {strategy.trades:2d} trades | ${final_value:>10,.2f}")

# Find best strategy
best = max(results, key=lambda x: x['Return'])

print(f"\n--- WINNER ---")
print(f"{best['Strategy']} with {best['Return']:.2f}% return")
print(f"\nNext Step: Use {best['Strategy']} as your primary strategy!")
print(f"Or combine multiple strategies for better diversification.")
