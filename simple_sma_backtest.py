# Day 4: Your first backtest with backtrader
# SMA (Simple Moving Average) Crossover strategy 
# Buy when SMA(10) crosses above SMA(30)
# Sell when SMA(10) crosses below SMA(30)

import backtrader as bt 
import yfinance as yf 
from datetime import datetime

class SMAStrategy(bt.Strategy):
    """Simple Moving Average Crossover Strategy"""

    def __init__(self):
        #Calculate moving averages 
        self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period = 10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period = 30)
        self.crossover = bt.indicators.CrossOver(self.sma10, self.sma30)

        self.trades = 0 
        self.wins = 0 
        self.losses = 0 

    def next(self):
        """Called on each bar (day) of data"""

        if not self.position: #Not in a trade
            if self.crossover > 0: #SMA10 crossed above SMA30 = Buy signal
                self.buy()
                self.trades += 1
        else: #In a trade
            if self.crossover < 0: #SMA10 crossed below SMA30 = SELL signal
                self.sell()

# Create a Cerebro engine (backtrader's main engine)

cerebro = bt.Cerebro()

cerebro.addstrategy(SMAStrategy)

#Download data 
print("Downloading SPY data for 2025...")
data = yf.download('SPY', start = '2025-01-01', end='2025-12-31', progress = False)

# Fix multi-index columns from yfinance
if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
    data.columns = data.columns.get_level_values(0)

#Create a data feed 
data_feed = bt.feeds.PandasData(dataname = data)
cerebro.adddata(data_feed)

#Set initial cash
cerebro.broker.setcash(10000)

#Run backtest
print("\n Running backtest...")
results = cerebro.run()
strategy = results[0]

#Get final portfolio value
final_value = cerebro.broker.getvalue()
total_return = ((final_value - 10000)/ 10000) * 100

print(f"\n=== BACKTEST RESULTS ===")
print(f"Starting Cash: $10,000")
print(f"Final Value: ${final_value:.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"Total Trades: {strategy.trades}")
print(f"Wins: {strategy.wins}")
print(f"Losses: {strategy.losses}")