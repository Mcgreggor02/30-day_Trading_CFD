#Day 5 
# Test different SMA combinations to fidn the best one 

import backtrader as bt 
import yfinance as yf
import pandas as pd 

class OptimizableSMAStrategy(bt.Strategy):
    """SMA strategy with configurable parameters"""

    params = (
        ('sma1_period', 10), #Will be changed during optimization
        ('sma2_period', 30), #Will be changed during optimization
    )

    def __init__(self):
        self.sma1 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma1_period)
        self.sma2 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma2_period)
        self.crossover = bt.indicators.CrossOver(self.sma1, self.sma2)

        self.trade_count = 0
    def next(self):
        """Called on each bar"""

        if not self.position:
            if self.crossover > 0: #BUY
                self.buy()
                self.trade_count += 1
        else:
            if self.crossover < 0: #Sell 
                self.sell()

# Download data once 
print("Downloading SPY data for 2023...")
data = yf.download('SPY', start = '2023-01-01', end='2023-12-31', progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

#Test different SMA combinations 
results = []

sma_combinations = [
    (5,15),
    (10,30),
    (20,50),
    (5,20),
    (10,50),
]


print("\n === TESTING SMA PARAMETER COMBINATIONS ===\n")

for sma1,sma2 in sma_combinations:
    cerebro = bt.Cerebro()
    cerebro.addstrategy(OptimizableSMAStrategy,sma1_period=sma1,sma2_period=sma2)

    #Add data 
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    #Set cash
    cerebro.broker.setcash(10000)

    #Run backtest
    strats = cerebro.run()
    strategy = strats[0]

    final_value = cerebro.broker.getvalue()
    total_return = ((final_value - 10000)/10000) * 100

    results.append({
        'SMA1' :sma1,
        'SMA2' : sma2,
        'Return': total_return,
        'Trades' : strategy.trade_count,
        'Final Value' : final_value
    })

    print(f"SMA({sma1:2d},{sma2:2d}): {total_return:>7.2f}% return | {strategy.trade_count:2d} trades | Final: ${final_value:,.2f}")

# Find best strategy
best_strategy = max(results, key=lambda x: x['Return'])

print(f"\n--- BEST PARAMETER COMBINATION ---")
print(f"SMA({best_strategy['SMA1']},{best_strategy['SMA2']}) with {best_strategy['Return']:.2f}% return")
print(f"Total Trades: {best_strategy['Trades']}")
print(f"Final Value: ${best_strategy['Final Value']:.2f}")
