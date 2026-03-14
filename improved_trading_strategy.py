# Day 8: Balanced Trading Strategy with Smart Filters
# The previous version was too protective (0 trades)
# This version balances risk protection with opportunity capture

import backtrader as bt
import yfinance as yf
import numpy as np

class BalancedSMAStrategy(bt.Strategy):
    """
    Balanced SMA strategy with smart filters:
    1. Volatility filter (scale position size, not block trades)
    2. Trend confirmation (only for new entries, not exits)
    3. Protective stop-loss
    """
    
    def __init__(self):
        # Original SMA indicators
        self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period=10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period=30)
        self.crossover = bt.indicators.CrossOver(self.sma10, self.sma30)
        
        # Protective filters
        self.volatility = bt.indicators.StandardDeviation(self.data.close, period=20)
        self.sma50 = bt.indicators.SimpleMovingAverage(self.data.close, period=50)
        
        # Track performance
        self.trades = 0
        self.entry_price = None
        self.max_drawdown = 0
        self.peak_value = 10000
    
    def next(self):
        """Called on each bar"""
        
        # Update drawdown tracking
        current_value = self.broker.getvalue()
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        current_drawdown = (self.peak_value - current_value) / self.peak_value
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # SMART FILTER: Use volatility to scale position size, not block trades
        position_size = 1.0  # Full position
        if self.volatility[0] > 2.5:
            position_size = 0.5  # Half position in high volatility
        elif self.volatility[0] > 2.0:
            position_size = 0.75  # 75% position in elevated volatility
        
        # Original signal (with confirmation)
        if not self.position:
            if self.crossover > 0:  # BUY signal
                # Add confirmation: price above 50-day MA for safety
                if self.data.close[0] > self.sma50[0]:
                    self.buy(size=position_size)
                    self.entry_price = self.data.close[0]
                    self.trades += 1
        else:
            # Exit signals
            if self.crossover < 0:  # SMA crossover signal
                self.sell()
            # Protective stop-loss: exit if price drops 3% below entry
            elif self.entry_price and self.data.close[0] < self.entry_price * 0.97:
                self.sell()

print("=== BALANCED TRADING STRATEGY TEST ===\n")

# Test on 2022 (the year original strategy failed)
print("Testing on 2022 (bear market):\n")

data = yf.download('SPY', start='2022-01-01', end='2022-12-31', progress=False)
if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
        data.columns = data.columns.get_level_values(0)

cerebro = bt.Cerebro()
cerebro.addstrategy(BalancedSMAStrategy)

data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)
cerebro.broker.setcash(10000)

results = cerebro.run()
strategy = results[0]

final_value = cerebro.broker.getvalue()
total_return = ((final_value - 10000) / 10000) * 100

print(f"2022 RESULTS (Bear Market):")
print(f"Starting Capital: $10,000")
print(f"Final Value: ${final_value:.2f}")
print(f"Return: {total_return:.2f}%")
print(f"Total Trades: {strategy.trades}")
print(f"Max Drawdown: {strategy.max_drawdown*100:.2f}%")

print(f"\n--- COMPARISON ---")
print(f"Original SMA (Day 4):  2022 = -0.45% return | 4 trades")
print(f"Balanced SMA (Day 8):  2022 = {total_return:.2f}% return | {strategy.trades} trades")

if total_return > -0.45:
    improvement = total_return - (-0.45)
    print(f"✓ IMPROVEMENT of {improvement:.2f} percentage points!")
else:
    print(f"Strategy is challenging in bear market")

# Test across multiple years with balanced strategy
print(f"\n\n=== TESTING BALANCED STRATEGY ACROSS 3 YEARS ===\n")

years = ['2023', '2022', '2021']
results_data = []

for year in years:
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BalancedSMAStrategy)
    
    data = yf.download('SPY', start=start_date, end=end_date, progress=False)
    if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
        data.columns = data.columns.get_level_values(0)
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000)
    
    strats = cerebro.run()
    strategy = strats[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = ((final_value - 10000) / 10000) * 100
    
    results_data.append({
        'year': year,
        'return': total_return,
        'trades': strategy.trades,
        'max_dd': strategy.max_drawdown
    })
    
    print(f"{year}: {total_return:>7.2f}% return | {strategy.trades:2d} trades | Max DD: {strategy.max_drawdown*100:5.2f}%")

print(f"\n--- SUMMARY ---")
avg_return = np.mean([r['return'] for r in results_data])
avg_trades = np.mean([r['trades'] for r in results_data])
print(f"Average return across 3 years: {avg_return:.2f}%")
print(f"Average trades per year: {avg_trades:.1f}")

# Compare to originals
print(f"\n--- COMPARISON TO ORIGINALS ---")
original_results = {
    '2023': 0.62,
    '2022': -0.45,
    '2021': 0.53
}

for r in results_data:
    original = original_results[r['year']]
    diff = r['return'] - original
    if diff > 0:
        print(f"{r['year']}: {original:+.2f}% (original) → {r['return']:+.2f}% (improved) [+{diff:.2f}%]")
    else:
        print(f"{r['year']}: {original:+.2f}% (original) → {r['return']:+.2f}% (improved) [{diff:.2f}%]")

print(f"\n=== SESSION 2 COMPLETE ===")