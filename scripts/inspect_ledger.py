import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json

LEDGER_PATH = Path("/data/data/com.termux/files/home/GitHub_Workspace/Kimi-K2/ledger.json")

def inspect_ledger():
    if not LEDGER_PATH.exists():
        print(f"❌ Ledger file not found at: {LEDGER_PATH}")
        return

    with open(LEDGER_PATH, "r") as f:
        data = json.load(f)

    balances = data.get("balances", {}) if isinstance(data, dict) else {}
    transactions = data.get("transactions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    print("=== SOVEREIGN LEDGER BALANCES ===")
    for node, balance in balances.items():
        print(f"  {node:<20}: {balance:,} sats")

    print(f"\n=== RECENT TRANSACTIONS (Total: {len(transactions)}) ===")
    for tx in transactions[-5:]:
        tx_id = tx.get("tx_id", "N/A")
        origin = tx.get("origin", "UNKNOWN")
        budget = tx.get("total_budget", 0)
        hops = " -> ".join(tx.get("hops", []))
        allocs = tx.get("allocations", {})
        print(f"  TX: {tx_id}")
        print(f"    Origin: {origin} | Budget: {budget} sats")
        print(f"    Hops: {hops}")
        print(f"    Allocations: {allocs}\n")

if __name__ == "__main__":
    inspect_ledger()
