#Day 2: Trading signals Generator 
#This demonstrates if/else loginv for trading decisions 

def generate_signal(price_change_pt):
    """ 
    Generate a trading signal based on price change 
    Returns: 'Buy', 'Sell', or 'Hold'
    """

    if price_change_pt > 2: #Price up more than 2%
        return "SELL" # Take Profit 
    elif price_change_pt < -2: #Price down more than 2%
        return "BUY" #Buy the dip (mean reversion)
    else:
        return "HOLD" #Wait for bigger move
    
# Test the function with different scenarios 
testCases =[
    3.5, #Up 3.5% (SELL)
    -2.5, #Down 2.5% (BUY)
    1.2, #Up 1.2% (HOLD)
    -0.5, #Down .5% (HOLD)
    5.0 #Up 5% (SELL)
]

print("=== TRADING SIGNAL TEST ===\n")
for price_Change in testCases:
    signal= generate_signal(price_Change)
    print(f"Price change: {price_Change:>5}% → Signal: {signal}")