import sqlite3
import csv
import os

DB_PATH = os.path.expanduser("~/Tordial-GS/scripts/manifold_cascade.db")
CSV_PATH = os.path.expanduser("~/Tordial-GS/scripts/manifold_telemetry_100.csv")

def export_csv():
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

    with open(CSV_PATH, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "step_index", 
            "status", 
            "boundary", 
            "scale_omega_hex", 
            "scale_omega_dec", 
            "flux_accumulator_hex", 
            "flux_accumulator_dec", 
            "effective_delta_x", 
            "depth_k", 
            "backpressure_pct"
        ])
        
        for r in rows:
            step_idx, status, boundary, scale_hex, flux_hex, k, throttle = r
            scale_dec = int(scale_hex, 16)
            flux_dec = int(flux_hex, 16)
            delta_x = (flux_dec * scale_dec) >> 32
            writer.writerow([
                step_idx, status, boundary, scale_hex, scale_dec, flux_hex, flux_dec, delta_x, k, throttle
            ])

    print(f"[+] Successfully exported {len(rows)} steps to {CSV_PATH}")

if __name__ == "__main__":
    export_csv()
