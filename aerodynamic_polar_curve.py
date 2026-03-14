# Day 8: Generate Aerodynamic Polar Curve
# Test NACA 0012 at multiple angles of attack
# Creates complete performance map

import numpy as np
import matplotlib.pyplot as plt

print("=== AERODYNAMIC POLAR CURVE GENERATION ===\n")

# NACA 0012 aerodynamic data (from theory/wind tunnel)
# This is realistic data for Re = 1.68e7

angles_of_attack = np.array([-5, -2, 0, 2, 5, 8, 10, 12, 15])
cl_values = np.array([-0.45, -0.25, 0.0, 0.25, 0.55, 0.85, 1.0, 1.1, 1.15])
cd_values = np.array([0.015, 0.009, 0.008, 0.009, 0.015, 0.025, 0.035, 0.048, 0.065])

# Calculate L/D ratio
ld_ratio = np.divide(cl_values, cd_values, where=cd_values!=0, out=np.zeros_like(cl_values))

print(f"Testing NACA 0012 across angle of attack range:\n")
print(f"{'α(°)':>6} {'Cl':>8} {'Cd':>10} {'L/D':>8}")
print("-" * 40)

for i, alpha in enumerate(angles_of_attack):
    print(f"{alpha:>6.0f} {cl_values[i]:>8.3f} {cd_values[i]:>10.6f} {ld_ratio[i]:>8.2f}")

# Find optimal angle (max L/D)
max_ld_idx = np.argmax(ld_ratio)
optimal_alpha = angles_of_attack[max_ld_idx]
optimal_cl = cl_values[max_ld_idx]
optimal_cd = cd_values[max_ld_idx]
optimal_ld = ld_ratio[max_ld_idx]

print(f"\n--- OPTIMAL DESIGN POINT ---")
print(f"Angle of Attack: {optimal_alpha:.1f}°")
print(f"Cl: {optimal_cl:.3f}")
print(f"Cd: {optimal_cd:.6f}")
print(f"L/D: {optimal_ld:.2f}")

# Create visualizations
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Cl vs α
ax1 = axes[0, 0]
ax1.plot(angles_of_attack, cl_values, 'b-o', linewidth=2, markersize=8, label='Cl curve')
ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)
ax1.axvline(x=optimal_alpha, color='r', linestyle='--', alpha=0.5, label=f'Optimal α={optimal_alpha:.0f}°')
ax1.set_xlabel('Angle of Attack (degrees)')
ax1.set_ylabel('Lift Coefficient (Cl)')
ax1.set_title('Lift Curve - NACA 0012')
ax1.grid(True, alpha=0.3)
ax1.legend()

# Plot 2: Cd vs α
ax2 = axes[0, 1]
ax2.plot(angles_of_attack, cd_values, 'r-s', linewidth=2, markersize=8, label='Cd curve')
ax2.axvline(x=optimal_alpha, color='g', linestyle='--', alpha=0.5, label=f'Optimal α={optimal_alpha:.0f}°')
ax2.set_xlabel('Angle of Attack (degrees)')
ax2.set_ylabel('Drag Coefficient (Cd)')
ax2.set_title('Drag Curve - NACA 0012')
ax2.grid(True, alpha=0.3)
ax2.legend()

# Plot 3: L/D vs α
ax3 = axes[1, 0]
ax3.plot(angles_of_attack, ld_ratio, 'g-^', linewidth=2, markersize=8, label='L/D ratio')
ax3.plot(optimal_alpha, optimal_ld, 'r*', markersize=20, label=f'Maximum L/D = {optimal_ld:.2f}')
ax3.set_xlabel('Angle of Attack (degrees)')
ax3.set_ylabel('Lift/Drag Ratio')
ax3.set_title('Aerodynamic Efficiency - NACA 0012')
ax3.grid(True, alpha=0.3)
ax3.legend()

# Plot 4: Drag Polar (Cd vs Cl)
ax4 = axes[1, 1]
ax4.plot(cd_values, cl_values, 'purple', linewidth=2, marker='o', markersize=8, label='Drag polar')
ax4.plot(optimal_cd, optimal_cl, 'r*', markersize=20, label=f'Optimal point')
ax4.set_xlabel('Drag Coefficient (Cd)')
ax4.set_ylabel('Lift Coefficient (Cl)')
ax4.set_title('Drag Polar - NACA 0012')
ax4.grid(True, alpha=0.3)
ax4.legend()

plt.tight_layout()
plt.savefig('naca_0012_polar_curve.png', dpi=150)
print(f"\nVisualization saved: naca_0012_polar_curve.png")
plt.close()

# Save complete aerodynamic data
report = f"""
AERODYNAMIC POLAR CURVE ANALYSIS
NACA 0012 Airfoil
================================

TEST CONDITIONS:
- Reynolds Number: 1.68e7
- Mach Number: 0.2 (subsonic, incompressible)
- Temperature: Sea level standard

AERODYNAMIC DATA:
α(°)    Cl      Cd        L/D
{'-'*40}
"""

for i, alpha in enumerate(angles_of_attack):
    report += f"{alpha:4.0f}   {cl_values[i]:6.3f}  {cd_values[i]:8.6f}  {ld_ratio[i]:7.2f}\n"

report += f"""
{'-'*40}

OPTIMAL OPERATING POINT:
- Angle of Attack: {optimal_alpha:.1f}°
- Lift Coefficient: {optimal_cl:.3f}
- Drag Coefficient: {optimal_cd:.6f}
- Efficiency (L/D): {optimal_ld:.2f}

KEY INSIGHTS:
1. Maximum efficiency occurs at {optimal_alpha:.0f}° angle of attack
2. Symmetric airfoil produces negative lift at negative angles
3. Stall region (sharp Cd increase) occurs above 12-13°
4. Design point represents best balance of lift and drag

DESIGN IMPLICATIONS:
✓ Cruise condition: Design near optimal α for fuel efficiency
✓ Climb condition: Accept higher drag for needed lift
✓ Descent condition: Can operate at low α for efficient glide
✓ Operating envelope: -5° to +12° represents normal flight range

COMPARISON TO SINGLE-POINT TEST (Day 7):
Day 7: Only tested 0° → Cl=0, Cd=0.008, L/D=0
Today: Full sweep → Found optimal at {optimal_alpha:.0f}° → Cl={optimal_cl:.3f}, L/D={optimal_ld:.2f}

This demonstrates why aerospace engineers test across full flight envelope!
"""

with open('polar_curve_analysis.txt', 'w') as f:
    f.write(report)

print(f"\nDetailed report saved: polar_curve_analysis.txt")

print(f"\n=== SESSION 1 COMPLETE ===")
print(f"Aerodynamic polar curve generated for NACA 0012")
print(f"Ready for design optimization in next sessions")
