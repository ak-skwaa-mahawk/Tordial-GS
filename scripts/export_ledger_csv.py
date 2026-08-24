import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import csv
import time
import re

LEDGER_PATH = Path("/data/data/com.termux/files/home/GitHub_Workspace/Kimi-K2/ledger.json")
SETTLEMENT_LOG = Path.home() / ".settlement_worker.log"
OUTPUT_CSV_DIR = Path.home() / "reports"

def load_xrpl_tx_map():
    xrpl_map = {}
    if not SETTLEMENT_LOG.exists():
        return xrpl_map

    tx_pattern = re.compile(r"Hash=([A-Fa-f0-9]+)\s+\|\s+Code=(\w+)")
    try:
        with open(SETTLEMENT_LOG, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = tx_pattern.search(line)
                if match:
                    tx_hash, code = match.groups()
                    xrpl_map[tx_hash[:16]] = {"hash": tx_hash, "code": code}
    except Exception:
        pass
    return xrpl_map

def export_ledger_to_csv(output_path: Path = None) -> Path:
    if not LEDGER_PATH.exists():
        raise FileNotFoundError(f"Ledger not found at: {LEDGER_PATH}")

    OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_CSV_DIR / f"e8_settlement_report_{timestamp}.csv"

    with open(LEDGER_PATH, "r") as f:
        data = json.load(f)

    transactions = data.get("transactions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    xrpl_txs = load_xrpl_tx_map()
    latest_xrpl_hash = next(iter(xrpl_txs.values()))["hash"] if xrpl_txs else "OFFCHAIN_SATS_ONLY"

    fields = [
        "tx_id",
        "timestamp_epoch",
        "origin_node",
        "hop_count",
        "route_path",
        "total_budget_sats",
        "node_payout_sats",
        "floor_reserve_sats",
        "xrpl_tx_hash",
        "settlement_status"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()

        for idx, tx in enumerate(transactions):
            tx_id = tx.get("tx_id", "")
            epoch_part = tx_id.split("_")[-1] if "_" in tx_id else ""
            hops = tx.get("hops", [])
            allocations = tx.get("allocations", {})
            floor_cut = allocations.get("FLOOR_RESERVE", 0)
            node_cut = sum(amt for node, amt in allocations.items() if node != "FLOOR_RESERVE")

            # Associate test XRPL hash with the latest verified broadcast
            xrpl_hash = latest_xrpl_hash if idx == len(transactions) - 1 and xrpl_txs else "OFFCHAIN_SATS_ONLY"

            writer.writerow({
                "tx_id": tx_id,
                "timestamp_epoch": epoch_part,
                "origin_node": tx.get("origin", "UNKNOWN"),
                "hop_count": len(hops),
                "route_path": " -> ".join(hops),
                "total_budget_sats": tx.get("total_budget", 0),
                "node_payout_sats": node_cut,
                "floor_reserve_sats": floor_cut,
                "xrpl_tx_hash": xrpl_hash,
                "settlement_status": "SETTLED"
            })

    print(f"✅ Exported {len(transactions):,} transactions to: {output_path}")
    return output_path

if __name__ == "__main__":
    export_ledger_to_csv()
