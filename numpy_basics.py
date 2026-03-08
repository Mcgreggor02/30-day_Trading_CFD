#Day 3: Numpy Arrays 
#Numpy = fast mathematical opertions on arrays 

import numpy as np

#Create arrays 
prices = np.array([100,102,101,103,105,104,106,108])
print("=== NUMPY ARRAYS ===\n")
print(f"Prices: {prices}")
print(f"Type: {type(prices)}")

#Basic operations 
print(f"\n === ARRAY OPERATIONS ===")
print(f"Sum: {np.sum(prices)}")
print(f"Mean: {np.mean(prices):.2f}")
print(f"Std Dev: {np.std(prices):.2f}")
print(f"Min: {np.min(prices):.2f}")
print(f"Max: {np.max(prices):.2f}")


#Calculate returns 
returns = np.diff(prices) / prices[:-1] * 100
print(f"\n === DAILY RETURNS ===")
print(f"Returns: {returns}")
print(f"Avg Return: {np.mean(returns):.3f}%")

#Find positive returns
positive_returns = returns[returns > 0]
print(f"\n--- POSITIVE RETURNS ---")
print(f"Positive days: {len(positive_returns)}")
print(f"Average positive return: {np.mean(positive_returns):.3f}%")
