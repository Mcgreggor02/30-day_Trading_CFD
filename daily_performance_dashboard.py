# Day 13: Daily Performance Dashboard
# Track signal accuracy and P&L

import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
import numpy as np

print("=== DAILY PERFORMANCE DASHBOARD ===\n")

# Load today's signals
with open('ultimate_signals.json', 'r') as f:
    today_signals = json.load(f)

print("="*80)
print("TODAY'S SIGNAL PERFORMANCE (End of Day)")
print("="*80)

# Get current prices (end of day)
performance = []

print(f"\n{'Ticker':<8} {'Entry':<10} {'Current':<10} {'Change':<10} {'P&L':<10} {'Status'}")
print("-"*80)

for signal in today_signals:
    ticker = signal['ticker']
    entry_price = signal['price']
    
    # Get current price
    try:
        data = yf.download(ticker, period='1d', progress=False)
        if isinstance(data.columns, tuple) or hasattr(data.columns, 'levels'):
                    data.columns = data.columns.get_level_values(0)
        if len(data) > 0:
            current_price = data['Close'].iloc[-1]
            change_pct = (current_price - entry_price) / entry_price * 100
            pnl = current_price - entry_price
            
            status = "✓ WIN" if pnl > 0 else "✗ LOSS" if pnl < 0 else "→ FLAT"
            
            performance.append({
                'ticker': ticker,
                'entry': entry_price,
                'current': current_price,
                'change': change_pct,
                'pnl': pnl,
                'signal': signal['signal']
            })
            
            print(f"{ticker:<8} ${entry_price:<9.2f} ${current_price:<9.2f} {change_pct:>8.2f}% ${pnl:>8.2f} {status}")
    except:
        pass

# Performance summary
print("\n" + "="*80)
print("PERFORMANCE SUMMARY")
print("="*80)

df_perf = pd.DataFrame(performance)

if len(df_perf) > 0:
    winners = len(df_perf[df_perf['pnl'] > 0])
    losers = len(df_perf[df_perf['pnl'] < 0])
    win_rate = winners / len(df_perf) * 100 if len(df_perf) > 0 else 0
    total_pnl = df_perf['pnl'].sum()
    avg_gain = df_perf[df_perf['pnl'] > 0]['pnl'].mean() if winners > 0 else 0
    avg_loss = df_perf[df_perf['pnl'] < 0]['pnl'].mean() if losers > 0 else 0
    
    print(f"\nWinning trades: {winners}/{len(df_perf)} ({win_rate:.1f}%)")
    print(f"Losing trades: {losers}/{len(df_perf)}")
    print(f"Total P&L: ${total_pnl:.2f}")
    print(f"Average gain: ${avg_gain:.2f}")
    print(f"Average loss: ${avg_loss:.2f}")
    
    if winners > 0 and losers > 0:
        reward_risk = abs(avg_gain / avg_loss)
        print(f"Reward/Risk ratio: {reward_risk:.2f}x")

# Best and worst trades
print("\n" + "="*80)
print("BEST AND WORST TRADES")
print("="*80)

if len(df_perf) > 0:
    best = df_perf.nlargest(3, 'pnl')
    worst = df_perf.nsmallest(3, 'pnl')
    
    print("\nBEST 3:")
    for idx, row in best.iterrows():
        print(f"  {row['ticker']}: +${row['pnl']:.2f} ({row['change']:.2f}%)")
    
    print("\nWORST 3:")
    for idx, row in worst.iterrows():
        print(f"  {row['ticker']}: ${row['pnl']:.2f} ({row['change']:.2f}%)")

# Save performance
with open('daily_performance.json', 'w') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'signals_count': len(today_signals),
        'trades_analyzed': len(performance),
        'winners': winners if len(df_perf) > 0 else 0,
        'losers': losers if len(df_perf) > 0 else 0,
        'win_rate': win_rate if len(df_perf) > 0 else 0,
        'total_pnl': float(total_pnl) if len(df_perf) > 0 else 0,
        'performance': performance
    }, f, indent=2)

print(f"\n✓ Performance saved to: daily_performance.json")
print(f"=== DASHBOARD COMPLETE ===")