import sqlite3
import os

DB_PATH = os.path.expanduser("~/Tordial-GS/scripts/manifold_cascade.db")
EPSILON_GATE = 0x000418937

def analyze_ledger():
    if not os.path.exists(DB_PATH):
        print(f"[-] Ledger not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT step_index, status, boundary, scale_omega, flux_accumulator, depth_k, backpressure_pct
        FROM telemetry_ledger
        WHERE step_index <= 100
        ORDER BY step_index ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("[-] No records found.")
        return

    deltas = []
    fluid_count = 0
    coag_count = 0
    rupture_count = 0

    print("==========================================================================================")
    print("                      PHASE VELOCITY DISTRIBUTION ANALYSIS (STEPS 1 - 100)                ")
    print("==========================================================================================")
    print(f" Observer Gate Threshold (Epsilon) : 0x{EPSILON_GATE:08X} (~{EPSILON_GATE})")
    print("------------------------------------------------------------------------------------------")
    print(f"{'Step':<5} | {'Status':<10} | {'Boundary':<8} | {'k':<2} | {'Scale Omega':<12} | {'Effective ΔX (Dec)':<18} | {'ΔX vs ε'}")
    print("------------------------------------------------------------------------------------------")

    for row in rows:
        step_idx, status, boundary, scale_omega_str, flux_acc_str, depth_k, throttle = row

        scale_omega = int(scale_omega_str, 16)
        flux_acc = int(flux_acc_str, 16)

        # Reconstruct effective shift: delta_X = (flux * scale_omega) >> 32
        effective_delta_x = (flux_acc * scale_omega) >> 32
        deltas.append((step_idx, effective_delta_x, status, boundary, depth_k))

        gate_rel = "<= ε (LOCKED)" if effective_delta_x <= EPSILON_GATE else "> ε (DISPERSED)"

        if status == "FLUID":
            fluid_count += 1
        elif status == "COAGULATED":
            coag_count += 1
        
        if boundary == "RUPTURED":
            rupture_count += 1

        # Print transition milestones and boundary crossings
        if step_idx <= 5 or step_idx >= 94 or boundary == "RUPTURED":
            print(f"{step_idx:<5} | {status:<10} | {boundary:<8} | {depth_k:<2} | {scale_omega_str:<12} | {effective_delta_x:<18} | {gate_rel}")
        elif step_idx == 6:
            print(f"{'...':<5} | {'...':<10} | {'...':<8} | {'..'} | {'...':<12} | {'...':<18} | {'...'}")

    print("------------------------------------------------------------------------------------------")
    
    # Distribution Statistics
    raw_shifts = [d[1] for d in deltas]
    min_shift = min(raw_shifts)
    max_shift = max(raw_shifts)
    avg_shift = sum(raw_shifts) / len(raw_shifts)

    print(f"\n[+] Distribution Summary:")
    print(f"  • Total Steps Recorded       : {len(deltas)}")
    print(f"  • Fluid Steps (> ε)          : {fluid_count}")
    print(f"  • Coagulated Steps (<= ε)    : {coag_count}")
    print(f"  • Boundary Rupture Events    : {rupture_count}")
    print(f"  • Minimum Coordinate Shift   : {min_shift} (0x{min_shift:X})")
    print(f"  • Maximum Coordinate Shift   : {max_shift} (0x{max_shift:X})")
    print(f"  • Mean Phase Velocity (ΔX)   : {avg_shift:.2f}")

    # Histogram Bins
    bin_sub_eps = sum(1 for x in raw_shifts if x <= EPSILON_GATE)
    bin_mid_flux = sum(1 for x in raw_shifts if EPSILON_GATE < x <= 10_000_000_000)
    bin_high_flux = sum(1 for x in raw_shifts if x > 10_000_000_000)

    print("\n[+] Curvature Gate Quantization:")
    print(f"  • Gate-Trapped (ΔX <= ε)     : {bin_sub_eps:<3} [{'#' * int(bin_sub_eps / 2):<20}] ({bin_sub_eps}%)")
    print(f"  • Intermediate (ε < ΔX <= 10G): {bin_mid_flux:<3} [{'#' * int(bin_mid_flux / 2):<20}] ({bin_mid_flux}%)")
    print(f"  • Surge Saturated (ΔX > 10G) : {bin_high_flux:<3} [{'#' * int(bin_high_flux / 2):<20}] ({bin_high_flux}%)")
    print("==========================================================================================")

if __name__ == "__main__":
    analyze_ledger()
