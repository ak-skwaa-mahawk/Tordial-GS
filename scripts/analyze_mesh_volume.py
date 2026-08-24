import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
from collections import Counter

LEDGER_PATH = Path("/data/data/com.termux/files/home/GitHub_Workspace/Kimi-K2/ledger.json")

def analyze_mesh_volume():
    if not LEDGER_PATH.exists():
        print(f"❌ Ledger file not found at: {LEDGER_PATH}")
        return

    with open(LEDGER_PATH, "r") as f:
        data = json.load(f)

    transactions = data.get("transactions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    balances = data.get("balances", {}) if isinstance(data, dict) else {}

    total_txs = len(transactions)
    if total_txs == 0:
        print("ℹ️ No transactions recorded yet.")
        return

    total_volume_sats = sum(tx.get("total_budget", 0) for tx in transactions)
    total_floor_sats = sum(tx.get("allocations", {}).get("FLOOR_RESERVE", 0) for tx in transactions)
    total_node_payouts = total_volume_sats - total_floor_sats
    
    hop_lengths = [len(tx.get("hops", [])) for tx in transactions]
    avg_hops = sum(hop_lengths) / total_txs if total_txs else 0.0

    origin_counts = Counter(tx.get("origin", "UNKNOWN") for tx in transactions)

    print("==========================================================")
    print("📊 TORDIAL E8 MESH ROUTING & FEE ANALYTICS")
    print("==========================================================")
    print(f"Total Settled Transactions : {total_txs:,}")
    print(f"Total Gross Volume Routed  : {total_volume_sats:,} sats")
    print(f"Total Node Payouts         : {total_node_payouts:,} sats ({(total_node_payouts/total_volume_sats)*100:.1f}%)")
    print(f"Total Floor Reserve Sunk   : {total_floor_sats:,} sats ({(total_floor_sats/total_volume_sats)*100:.1f}%)")
    print(f"Average Hops per Burst     : {avg_hops:.2f}")

    print("\n--- ORIGIN DISTRIBUTION ---")
    for origin, count in origin_counts.most_common():
        pct = (count / total_txs) * 100
        print(f"  {origin:<20}: {count:,} bursts ({pct:.1f}%)")

    print("\n--- CURRENT UNSPENT BALANCES ---")
    for node, bal in balances.items():
        print(f"  {node:<20}: {bal:,} sats")
    print("==========================================================\n")

if __name__ == "__main__":
    analyze_mesh_volume()
