import json
import os
import tempfile
import time
from typing import Dict, Any, List

LEDGER_PATH = "/data/data/com.termux/files/home/GitHub_Workspace/Kimi-K2/ledger.json"

DEFAULT_LEDGER = {
    "version": "1.0.0",
    "updated_at": 0,
    "total_gross_volume_sats": 0,
    "balances": {
        "FLOOR_RESERVE": 207300,
        "HEADSCALE-ALPHA": 5000,
        "HEADSCALE-BETA": 5000,
        "HEADSCALE-GAMMA": 5000,
        "ALPHA": 13650,
        "GAMMA": 11700,
        "BETA": 7050,
        "TORDIAL-EDGE-01": 933300
    },
    "transactions": []
}

class SovereignLedgerEngine:
    def __init__(self, ledger_file: str = LEDGER_PATH):
        self.ledger_file = ledger_file
        self.ensure_ledger_exists()

    def ensure_ledger_exists(self):
        if not os.path.exists(self.ledger_file):
            os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
            self._atomic_save(DEFAULT_LEDGER)

    def _atomic_save(self, data: dict):
        dir_name = os.path.dirname(self.ledger_file)
        os.makedirs(dir_name, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False) as tf:
            json.dump(data, tf, indent=2)
            temp_name = tf.name
        os.replace(temp_name, self.ledger_file)

    def load_ledger(self) -> dict:
        try:
            with open(self.ledger_file, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_LEDGER.copy()

    def settle_burst_dispatch(self, handoff_entry: dict, budget_sats: int = 500) -> dict:
        ledger = self.load_ledger()
        balances = ledger.setdefault("balances", {})
        
        origin = handoff_entry.get("origin", "TORDIAL-EDGE-01")
        trace = handoff_entry.get("trace", [])
        
        # Identify nodes that successfully dispatched an E8 highway hop
        dispatched_nodes = [
            hop.get("node_id") for hop in trace 
            if hop.get("status") == "E8_HIGHWAY_DISPATCHED" and hop.get("node_id")
        ]

        if not dispatched_nodes:
            return {
                "tx_id": None,
                "status": "NO_REWARDS_ZERO_DISPATCH",
                "origin": origin,
                "hops": [],
                "allocations": {},
                "total_budget": budget_sats
            }

        floor_cut = int(budget_sats * 0.10)
        net_budget = budget_sats - floor_cut
        per_node_cut = int(net_budget / len(dispatched_nodes))

        allocations = {"FLOOR_RESERVE": floor_cut}
        balances["FLOOR_RESERVE"] = balances.get("FLOOR_RESERVE", 0) + floor_cut

        for node in dispatched_nodes:
            allocations[node] = allocations.get(node, 0) + per_node_cut
            balances[node] = balances.get(node, 0) + per_node_cut

        ledger["total_gross_volume_sats"] = ledger.get("total_gross_volume_sats", 0) + budget_sats
        ledger["updated_at"] = time.time()

        tx_record = {
            "tx_id": f"tx_e8_{int(time.time()*1000)}_{origin}",
            "timestamp": time.time(),
            "origin": origin,
            "hops": dispatched_nodes,
            "total_budget": budget_sats,
            "allocations": allocations,
            "status": "SETTLED"
        }

        tx_list = ledger.setdefault("transactions", [])
        tx_list.append(tx_record)
        if len(tx_list) > 2500:
            ledger["transactions"] = tx_list[-2500:]

        self._atomic_save(ledger)
        return tx_record
