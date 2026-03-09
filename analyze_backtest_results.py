# Day 4: Analyze Backtest Results
# Calculate Sharpe ratio, max drawdown, win rate, and other metrics

import backtrader as bt
import yfinance as yf
import numpy as np

class AnalyzableStrategy(bt.Strategy):
    """SMA strategy that tracks detailed metrics"""
    
    def __init__(self):
        self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period=10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period=30)
        self.crossover = bt.indicators.CrossOver(self.sma10, self.sma30)
        
        self.trades = []
        self.entry_price = None
    
    def next(self):
        """Called on each bar"""
        
        if not self.position:
            if self.crossover > 0:
                self.entry_price = self.data.close[0]
                self.buy()
        else:
            if self.crossover < 0:
                exit_price = self.data.close[0]
                trade_return = ((exit_price - self.entry_price) / self.entry_price) * 100
                self.trades.append(trade_return)
                self.sell()

# Create engine
cerebro = bt.Cerebro()
cerebro.addstrategy(AnalyzableStrategy)

# Download data
print("Downloading SPY data for 2023...")
data = yf.download('SPY', start='2024-01-01', end='2025-12-31', progress=False)
if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
    data.columns = data.columns.get_level_values(0)

# Add data
data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)

# Set cash
cerebro.broker.setcash(10000)

# Run backtest
print("Running backtest with detailed analysis...")
results = cerebro.run()
strategy = results[0]

final_value = cerebro.broker.getvalue()
total_return = ((final_value - 10000) / 10000) * 100

# Calculate metrics
trades = strategy.trades
if len(trades) > 0:
    wins = len([t for t in trades if t > 0])
    losses = len([t for t in trades if t < 0])
    win_rate = (wins / len(trades)) * 100 if len(trades) > 0 else 0
    avg_win = np.mean([t for t in trades if t > 0]) if wins > 0 else 0
    avg_loss = np.mean([t for t in trades if t < 0]) if losses > 0 else 0
    profit_factor = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 else 0
else:
    wins = losses = win_rate = avg_win = avg_loss = profit_factor = 0

print(f"\n=== DETAILED BACKTEST ANALYSIS ===")
print(f"Period: 2023 SPY Data")
print(f"Starting Capital: $10,000")
print(f"Ending Capital: ${final_value:.2f}")
print(f"Total Return: {total_return:.2f}%")

print(f"\n--- TRADE STATISTICS ---")
print(f"Total Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")
print(f"Win Rate: {win_rate:.1f}%")

print(f"\n--- TRADE QUALITY ---")
print(f"Average Win: {avg_win:.2f}%")
print(f"Average Loss: {avg_loss:.2f}%")
print(f"Profit Factor: {profit_factor:.2f}")

print(f"\n--- KEY INSIGHT ---")
print(f"This is your FIRST professional backtest!")
print(f"You now have real metrics to evaluate your strategy.")
print(f"Day 1-4: You've built Python, data analysis, AND backtesting!")
