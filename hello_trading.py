#Day 1: First Trading Program 
#Calculates percentage return from entry/exit prices 

def calculate_return(entryPrice, exitPrice):
	"""Calculate percentage return on a trade"""
	return((exitPrice - entryPrice)/ entryPrice)*100

entry = 400
exit = 420

profitFn = calculate_return(entry,exit)

print(f"Entry Price: ${entry}")
print(f"Exit Price: ${exit}")
print(f"Your Return: {profitFn:.2f}%")