# Day 6: Create NACA 0012 Airfoil Coordinates
# First step to CFD: define the airfoil geometry

import numpy as np
import matplotlib.pyplot as plt

def naca_0012(num_points=100):
    """
    Generate NACA 0012 airfoil coordinates
    NACA 0012 = symmetric airfoil, 12% thickness
    """
    x = np.linspace(0, 1, num_points)
    
    # NACA 0012 thickness formula
    t = 0.12  # 12% thickness
    yt = 5 * t * (0.2969*np.sqrt(x) - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)
    
    # Upper surface
    x_upper = x
    y_upper = yt
    
    # Lower surface (symmetric)
    x_lower = x[::-1]
    y_lower = -yt[::-1]
    
    # Combine
    x_airfoil = np.concatenate([x_upper, x_lower])
    y_airfoil = np.concatenate([y_upper, y_lower])
    
    return x_airfoil, y_airfoil

# Generate airfoil
x, y = naca_0012(100)

print("=== NACA 0012 AIRFOIL MESH ===\n")
print(f"Generated {len(x)} coordinate points")
print(f"X range: {min(x):.3f} to {max(x):.3f}")
print(f"Y range: {min(y):.3f} to {max(y):.3f}")
print(f"Max thickness: {max(y):.3f}")

# Save coordinates to file (CFD will use this)
with open('naca_0012_coordinates.txt', 'w') as f:
    f.write("x\t\ty\n")
    for xi, yi in zip(x, y):
        f.write(f"{xi:.6f}\t{yi:.6f}\n")

print(f"\nCoordinates saved to: naca_0012_coordinates.txt")

# Visualization
plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', linewidth=2, label='NACA 0012')
plt.axis('equal')
plt.grid(True, alpha=0.3)
plt.xlabel('X (chord position)')
plt.ylabel('Y (thickness)')
plt.title('NACA 0012 Airfoil - Mesh Point Generation')
plt.legend()
plt.tight_layout()
plt.savefig('naca_0012_airfoil.png', dpi=150)
print("Plot saved to: naca_0012_airfoil.png")
plt.close()

print("\n=== NEXT STEPS ===")
print("1. These coordinates define the airfoil surface")
print("2. Next: Create a mesh AROUND the airfoil (in domain)")
print("3. Then: Run CFD solver to calculate flow")
print("4. Finally: Extract lift/drag forces")
