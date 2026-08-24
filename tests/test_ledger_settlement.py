import pytest
import json
from pathlib import Path
from core.mesh.ledger_settlement import SovereignLedgerEngine

@pytest.fixture
def temp_ledger(tmp_path):
    ledger_file = tmp_path / "test_ledger.json"
    engine = SovereignLedgerEngine(ledger_file=ledger_file)
    return engine

def test_ledger_settlement_distribution(temp_ledger):
    handoff_entry = {
        "origin": "NODE-ALPHA",
        "trace": [
            {"node_id": "NODE-ALPHA", "status": "E8_HIGHWAY_DISPATCHED"},
            {"node_id": "NODE-BETA", "status": "E8_HIGHWAY_DISPATCHED"}
        ]
    }
    
    res = temp_ledger.settle_burst_dispatch(handoff_entry, budget_sats=500)
    assert res["status"] == "SETTLED"
    
    allocations = res["allocations"]
    assert allocations["NODE-ALPHA"] == 225  # (500 * 0.90) / 2
    assert allocations["NODE-BETA"] == 225
    assert allocations["FLOOR_RESERVE"] == 50  # 500 - 450
    
    data = temp_ledger.load_ledger()
    assert data["balances"]["NODE-ALPHA"] == 225
    assert len(data["transactions"]) == 1

def test_ledger_zero_dispatch_noop(temp_ledger):
    handoff_entry = {
        "origin": "NODE-ALPHA",
        "trace": [
            {"node_id": "NODE-ALPHA", "status": "WEIGHTLESS_BURST_CATAPULTED"}
        ]
    }
    res = temp_ledger.settle_burst_dispatch(handoff_entry, budget_sats=500)
    assert res["status"] == "NO_REWARDS_ZERO_DISPATCH"
