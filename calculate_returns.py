#Day 2: Calculate Returns for Multiple Trades 
# This demonstrates loops for processing multiple data points

# Simulated trades: (entry, exit_price)
trades = [
    (100,105), # Trade 1
    (50,48), # Trade 2
    (200,220), # Trade 3
    (75,73), # Trade 4
    (150,155), # Trade 5
]

print("=== TRADE RETURNS ANALYSIS ===\n")

total_return = 0
winning_trades = 0 
losing_trades = 0 

# Loop through each trade 
for entry, exitPrice in trades:
    return_pct = ((exitPrice- entry)/entry) *100
    total_return += return_pct
    
    #count winner and losers 
    if return_pct > 0:
        winning_trades +=1
        result = "Win"
    else:
        losing_trades += 1
        result = "LOSS"
    print(f"Entry: ${entry:>3} → Exit: ${exitPrice:>3} | Return: {return_pct:>6.2f}% | {result}")





print(f"\n--- SUMMARY ---")
print(f"Total Trades: {len(trades)}")
print(f"Wins: {winning_trades}")
print(f"Losses: {losing_trades}")
print(f"Win Rate: {(winning_trades/len(trades))*100:.1f}%")
print(f"Total Return: {total_return:.2f}%")