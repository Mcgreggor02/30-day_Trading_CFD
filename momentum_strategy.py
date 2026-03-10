#Day 5 
# Test different SMA combinations to fidn the best one 

import backtrader as bt 
import yfinance as yf
import pandas as pd


class MomentumStrategy(bt.Strategy):
    """Momentum strategy - ride the trend"""



    def __init__(self):
        #Calculate momentum (10-day price change)
        self.momentum = self.data.close - self.data.close(-10)
        self.momentum_pct = (self.momentum/self.data.close(-10)) * 100

        #Calculate SMA for trend configuration
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period = 20)
        
        self.trades = 0
        
    def next(self):
        """Called on each bar"""

        if not self.position:
             # BUY when momentum is positive and price above SMA
            if self.momentum_pct[0] >1.5  and self.data.close[0] > self.sma[0]: #BUY
                self.buy()
                self.trades += 1
        else: #Sell when momentum turns negative
              if self.momentum_pct[0]  < -1.5  or self.data.close[0] < self.sma[0]: #BUY
                self.sell()


#Create engine 
cerebro = bt.Cerebro()
cerebro.addstrategy(MomentumStrategy)

# Download data once 
print("Downloading SPY data for 2023...")
data = yf.download('SPY', start = '2023-01-01', end='2023-12-31', progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)



#Add data 
data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)

#Set cash
cerebro.broker.setcash(10000)
#Run backtest
print("Running Momentum Strategy")
strats = cerebro.run()
strategy = strats[0]

final_value = cerebro.broker.getvalue()
total_return = ((final_value - 10000)/10000) * 100



print(f"\n=== MOMENTUM STRATEGY ===")
print(f"Starting Cash: $10,000")
print(f"Final Value: ${final_value:.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"Total Trades: {strategy.trades}")
print(f"\nStrategy Logic:")
print(f"  BUY: When momentum > 1.5% AND price above 20-day average (uptrend)")
print(f"  SELL: When momentum < -1.5% OR price below average (trend breaks)")