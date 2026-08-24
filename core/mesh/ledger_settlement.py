import json
import time
from pathlib import Path
from typing import Dict, Any, List, Union

LEDGER_PATH = Path("/data/data/com.termux/files/home/GitHub_Workspace/Kimi-K2/ledger.json")

class SovereignLedgerEngine:
    def __init__(self, ledger_file: Path = LEDGER_PATH):
        self.ledger_file = ledger_file
        self._ensure_ledger_exists()

    def _ensure_ledger_exists(self):
        if not self.ledger_file.parent.exists():
            self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_file.exists():
            initial_state = {
                "version": 1,
                "balances": {
                    "FLOOR_RESERVE": 100000,
                    "HEADSCALE-ALPHA": 5000,
                    "HEADSCALE-BETA": 5000,
                    "HEADSCALE-GAMMA": 5000
                },
                "transactions": []
            }
            with open(self.ledger_file, "w") as f:
                json.dump(initial_state, f, indent=2)

    def load_ledger(self) -> Dict[str, Any]:
        try:
            with open(self.ledger_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {
                        "version": 1,
                        "balances": {
                            "FLOOR_RESERVE": 100000,
                            "HEADSCALE-ALPHA": 5000,
                            "HEADSCALE-BETA": 5000,
                            "HEADSCALE-GAMMA": 5000
                        },
                        "transactions": data
                    }
                return data
        except Exception:
            return {"version": 1, "balances": {}, "transactions": []}

    def save_ledger(self, data: Dict[str, Any]):
        with open(self.ledger_file, "w") as f:
            json.dump(data, f, indent=2)

    def settle_burst_dispatch(self, handoff_entry: Dict[str, Any], budget_sats: int = 500) -> Dict[str, Any]:
        """
        Distributes satoshi rewards to intermediate forwarding nodes along the E8 highway.
        """
        trace = handoff_entry.get("trace", [])
        dispatched_hops = [h["node_id"] for h in trace if h.get("status") == "E8_HIGHWAY_DISPATCHED"]
        
        if not dispatched_hops:
            return {"status": "NO_REWARDS_ZERO_DISPATCH", "distributed_sats": 0}

        ledger_data = self.load_ledger()
        balances = ledger_data.setdefault("balances", {})
        transactions = ledger_data.setdefault("transactions", [])

        relayer_pool = int(budget_sats * 0.90)
        per_hop_reward = relayer_pool // len(dispatched_hops)
        floor_cut = budget_sats - (per_hop_reward * len(dispatched_hops))

        tx_id = f"tx_e8_{int(time.time() * 1000)}"
        tx_allocations = {}

        for node_id in dispatched_hops:
            balances[node_id] = balances.get(node_id, 0) + per_hop_reward
            tx_allocations[node_id] = per_hop_reward

        balances["FLOOR_RESERVE"] = balances.get("FLOOR_RESERVE", 0) + floor_cut
        tx_allocations["FLOOR_RESERVE"] = floor_cut

        tx_record = {
            "tx_id": tx_id,
            "timestamp": time.time(),
            "origin": handoff_entry.get("origin"),
            "hops": dispatched_hops,
            "total_budget": budget_sats,
            "allocations": tx_allocations
        }
        transactions.append(tx_record)
        self.save_ledger(ledger_data)

        return {
            "status": "SETTLED",
            "tx_id": tx_id,
            "allocations": tx_allocations
        }
