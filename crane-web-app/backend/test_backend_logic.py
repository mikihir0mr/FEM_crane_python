import sys
import os

# Add current directory to path so we can import crane_calc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crane_calc import calculate_crane

def test_calculation():
    print("Running crane calculation with default parameters...")
    try:
        results = calculate_crane({})
        
        print("\n--- Results ---")
        print(f"Tip Displacement DZ: {results['tip_displacement']['dz']}")
        print(f"Max Stress: {results['max_stress']}")
        
        if results['max_stress'] == 0.0:
            print("\n[FAIL] Max stress is 0.0. The calculation logic might be failing silently.")
            return False
        else:
            print(f"\n[PASS] Max stress is {results['max_stress']:.2f}")
            return True
            
    except Exception as e:
        print(f"\n[ERROR] Calculation failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_calculation()
    if not success:
        sys.exit(1)
