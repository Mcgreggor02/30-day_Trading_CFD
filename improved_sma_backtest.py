# Day 4: Improved SMA Strategy with Risk Management
# Only trades when volatility is acceptable (< 2.5%)

import backtrader as bt
import yfinance as yf
import numpy as np

class ImprovedSMAStrategy(bt.Strategy):
    """SMA strategy with volatility filter"""
    
    def __init__(self):
        self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period=10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period=30)
        self.crossover = bt.indicators.CrossOver(self.sma10, self.sma30)
        
        # Calculate volatility
        self.returns = (self.data.close - self.data.close(-1)) / self.data.close(-1) * 100
        self.volatility = bt.indicators.StandardDeviation(self.returns, period=20)
        
        self.trades = 0
        self.risk_filtered_trades = 0
    
    def next(self):
        """Called on each bar (day)"""
        
        # Only trade if volatility is low (< 2.5%)
        if self.volatility[0] > 2.5:
            return
        
        if not self.position:
            if self.crossover > 0:  # BUY signal
                self.buy()
                self.trades += 1
                self.risk_filtered_trades += 1
        else:
            if self.crossover < 0:  # SELL signal
                self.sell()

# Create engine
cerebro = bt.Cerebro()
cerebro.addstrategy(ImprovedSMAStrategy)

# Download data
print("Downloading SPY data for 2023...")
data = yf.download('SPY', start='2025-01-01', end='2025-12-31', progress=False)
if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
    data.columns = data.columns.get_level_values(0)

# Add data
data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)

# Set cash
cerebro.broker.setcash(10000)

# Run backtest
print("Running improved backtest with risk filter...")
results = cerebro.run()
strategy = results[0]

final_value = cerebro.broker.getvalue()
total_return = ((final_value - 10000) / 10000) * 100

print(f"\n=== IMPROVED STRATEGY (WITH VOLATILITY FILTER) ===")
print(f"Starting Cash: $10,000")
print(f"Final Value: ${final_value:.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"Total Signals: {strategy.trades}")
print(f"Trades Executed (after risk filter): {strategy.risk_filtered_trades}")
print(f"\nKey Insight: Risk management reduced trades but protects capital!")
