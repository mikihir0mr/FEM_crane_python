import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crane_calc import calculate_crane

def test_materials():
    # Base params
    base_params = {
        'pipe_od': 48.6,
        'base_len': 900.0,
        'base_wid': 600.0,
        'arm_pivot_height': 1800.0,
        'tripod_attach_height': 1000.0,
        'brace_mast_height': 800.0,
        'arm_len': 1000.0,
        'arm_angle': 180.0,
        'mass_tip': 100.0, # Heavy load to cause stress
    }

    print("--- Testing Material Changes ---")

    # Case 1: STK400 (t=2.4, yield=235)
    params_400 = base_params.copy()
    params_400['t_wall'] = 2.4
    params_400['yield_stress'] = 235.0
    res_400 = calculate_crane(params_400)
    
    # Case 2: STK500 (t=2.4, yield=355)
    params_500 = base_params.copy()
    params_500['t_wall'] = 2.4
    params_500['yield_stress'] = 355.0
    res_500 = calculate_crane(params_500)

    # Case 3: SuperLight700 (t=1.8, yield=700)
    params_700 = base_params.copy()
    params_700['t_wall'] = 1.8
    params_700['yield_stress'] = 700.0
    res_700 = calculate_crane(params_700)

    print(f"\n[STK400] t=2.4, yield=235")
    print(f"  Tip DZ: {res_400['tip_displacement']['dz']:.3f}")
    print(f"  Max Stress: {res_400['max_stress']:.3f}")
    print(f"  Failures: {len(res_400['failures'])}")

    print(f"\n[STK500] t=2.4, yield=355")
    print(f"  Tip DZ: {res_500['tip_displacement']['dz']:.3f}")
    print(f"  Max Stress: {res_500['max_stress']:.3f}")
    print(f"  Failures: {len(res_500['failures'])}")

    print(f"\n[SuperLight700] t=1.8, yield=700")
    print(f"  Tip DZ: {res_700['tip_displacement']['dz']:.3f}")
    print(f"  Max Stress: {res_700['max_stress']:.3f}")
    print(f"  Failures: {len(res_700['failures'])}")

    # Verification Logic
    # 1. STK400 vs STK500: DZ and Stress should be EQUAL. Failures might differ.
    if abs(res_400['tip_displacement']['dz'] - res_500['tip_displacement']['dz']) < 1e-6:
        print("\n[OK] STK400 vs STK500: Displacements are identical (Expected).")
    else:
        print("\n[FAIL] STK400 vs STK500: Displacements differ!")

    # 2. STK400 vs SuperLight700: DZ should differ (thinner wall -> more deflection).
    if abs(res_400['tip_displacement']['dz'] - res_700['tip_displacement']['dz']) > 0.1:
        print("[OK] STK400 vs SuperLight700: Displacements differ (Expected).")
    else:
        print("[FAIL] STK400 vs SuperLight700: Displacements are too similar!")

if __name__ == "__main__":
    test_materials()
