#Day 5 
# Test different SMA combinations to fidn the best one 

import backtrader as bt 
import yfinance as yf
import pandas as pd 

class MeanReversionStrategy(bt.Strategy):
    """MEAN Reversion Strategy -buy the dip"""



    def __init__(self):
        #Calculate 20-day moving average and standard deviation
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=20)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=20)

        #Calculate bands
        self.upper_band = self.sma + (2 * self.std)
        self.lower_band = self.sma - (2 * self.std)

        self.trades = 0
        
    def next(self):
        """Called on each bar"""

        current_price = self.data.close[0]

        if not self.position:
             # BUY when price goes below lower band (oversold)
            if current_price <self.lower_band[0]: #BUY
                self.buy()
                self.trades += 1
        else:
             # SELL when price returns to moving average (mean reversion)
            if current_price > self.sma[0]: #Sell 
                self.sell()


#Create engine 
cerebro = bt.Cerebro()
cerebro.addstrategy(MeanReversionStrategy)

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
print("Running mean reversion strategy")
strats = cerebro.run()
strategy = strats[0]

final_value = cerebro.broker.getvalue()
total_return = ((final_value - 10000)/10000) * 100



print(f"\n=== MEAN REVERSION STRATEGY ===")
print(f"Starting Cash: $10,000")
print(f"Final Value: ${final_value:.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"Total Trades: {strategy.trades}")
print(f"\nStrategy Logic:")
print(f"  BUY: When price drops 2 std dev below 20-day average (oversold)")
print(f"  SELL: When price returns to the 20-day average")