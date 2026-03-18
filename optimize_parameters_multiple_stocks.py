# Day 9: Parameter Optimization Across Multiple Stocks
# Find SMA parameters that work on SPY, QQQ, IWM, etc.
# Only keep parameters that work across MULTIPLE assets

import backtrader as bt
import yfinance as yf
import numpy as np

class OptimizableStrategy(bt.Strategy):
    params = (
        ('sma1', 10),
        ('sma2', 30),
    )
    
    def __init__(self):
        self.sma1 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma1)
        self.sma2 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma2)
        self.crossover = bt.indicators.CrossOver(self.sma1, self.sma2)
        self.trades = 0
    
    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
                self.trades += 1
        else:
            if self.crossover < 0:
                self.sell()

print("=== PARAMETER OPTIMIZATION ACROSS MULTIPLE STOCKS ===\n")

# Test parameters
sma_pairs = [
    (5, 15),
    (10, 30),
    (20, 50),
    (5, 20),
    (10, 50),
    (15, 45),
    (3, 10),
    (7, 21),
]

# Test stocks
stocks = ['SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'EEM']

# Store results: {(sma1, sma2): {stock: avg_return}}
results = {}

for sma1, sma2 in sma_pairs:
    results[(sma1, sma2)] = {}
    
    for ticker in stocks:
        yearly_returns = []
        
        for year in [2023, 2022, 2021]:
            try:
                cerebro = bt.Cerebro()
                cerebro.addstrategy(OptimizableStrategy, sma1=sma1, sma2=sma2)
                
                data = yf.download(ticker, start=f'{year}-01-01', end=f'{year}-12-31', progress=False)
                if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
                    data.columns = data.columns.get_level_values(0)
                
                if len(data) < sma2 + 10:  # Need enough data
                    yearly_returns.append(None)
                    continue
                
                data_feed = bt.feeds.PandasData(dataname=data)
                cerebro.adddata(data_feed)
                cerebro.broker.setcash(10000)
                
                strats = cerebro.run()
                strategy = strats[0]
                
                final_value = cerebro.broker.getvalue()
                total_return = ((final_value - 10000) / 10000) * 100
                yearly_returns.append(total_return)
                
            except Exception as e:
                yearly_returns.append(None)
        
        # Calculate average (ignore None values)
        valid_returns = [r for r in yearly_returns if r is not None]
        if valid_returns:
            avg_return = np.mean(valid_returns)
            results[(sma1, sma2)][ticker] = avg_return
        else:
            results[(sma1, sma2)][ticker] = None

# Print results in table format
print("PARAMETER PERFORMANCE ACROSS ALL STOCKS")
print("(3-year average return)\n")

print(f"{'SMA Pair':<12}", end='')
for stock in stocks:
    print(f"{stock:<12}", end='')
print(f"{'Average':<12} {'Best/Worst':<15}")
print("-" * 110)

best_overall = None
best_params_overall = None

for sma1, sma2 in sma_pairs:
    param_str = f"({sma1},{sma2})"
    print(f"{param_str:<12}", end='')
    
    stock_returns = []
    for stock in stocks:
        ret = results[(sma1, sma2)].get(stock)
        if ret is not None:
            stock_returns.append(ret)
            print(f"{ret:>10.2f}%  ", end='')
        else:
            print(f"{'N/A':<12}", end='')
    
    if stock_returns:
        avg = np.mean(stock_returns)
        best = max(stock_returns)
        worst = min(stock_returns)
        range_str = f"{worst:.1f}% to {best:.1f}%"
        
        print(f"{avg:>10.2f}%  {range_str:<15}")
        
        if best_overall is None or avg > best_overall:
            best_overall = avg
            best_params_overall = (sma1, sma2)
    else:
        print("No valid data")

print("\n" + "=" * 110)
print("ANALYSIS")
print("=" * 110)

if best_params_overall:
    print(f"\nBest Parameters Across All Stocks: SMA({best_params_overall[0]}, {best_params_overall[1]})")
    print(f"Average Return: {best_overall:.2f}%")
    
    print(f"\nPerformance by Stock with Best Parameters:")
    print(f"{'Stock':<10} {'Return':<12} {'Assessment'}")
    print("-" * 40)
    
    positive_count = 0
    for stock in stocks:
        ret = results[best_params_overall].get(stock)
        if ret is not None:
            status = "✓ Profitable" if ret > 0 else "✗ Loss"
            if ret > 0:
                positive_count += 1
            print(f"{stock:<10} {ret:>10.2f}%  {status:<12}")
    
    print(f"\nWins: {positive_count}/{len(stocks)} stocks profitable")
    
    print("\n" + "=" * 110)
    print("CRITICAL FINDING")
    print("=" * 110)
    
    if best_overall < 0:
        print(f"\n⚠️  EVEN BEST PARAMETERS LOSE MONEY: {best_overall:.2f}%")
        print(f"\nThis means simple SMA crossover strategies don't work for 2021-2023")
        print(f"\nWhy:")
        print(f"- 2021: Strong bull market (strategies lag)")
        print(f"- 2022: Strong bear market (strategies stop losses but miss rebounds)")
        print(f"- 2023: Strong bull market again (strategies lag)")
        print(f"\nMomentum markets favor buy-and-hold, not market-timing strategies")
        
        print(f"\nOPTIONS:")
        print(f"1. Add volatility-based filters (only trade when conditions favor mean-reversion)")
        print(f"2. Switch to momentum strategies (chase trends rather than mean-revert)")
        print(f"3. Use machine learning for better signal generation")
        print(f"4. Accept that this market favors buy-and-hold over active trading")
    
    elif best_overall > 0:
        print(f"\n✓ Found profitable parameters: {best_overall:.2f}% average")
        print(f"\nThis shows potential for funded trading!")
        print(f"\nNext: Refine these parameters and add filters")
    else:
        print(f"\n~ Parameters break even: {best_overall:.2f}%")
        print(f"\nMarginally viable, but need improvement")

print(f"\n=== TEST COMPLETE ===")