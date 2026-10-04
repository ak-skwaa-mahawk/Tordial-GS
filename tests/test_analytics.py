import json
from scripts.analyze_mesh_volume import analyze_mesh_volume
from core.mesh.ledger_settlement import SovereignLedgerEngine

def test_analyze_mesh_volume(capsys):
    engine = SovereignLedgerEngine()
    ledger_data = engine.load_ledger()
    original_txs = list(ledger_data.get("transactions", []))
    
    try:
        sample_tx = {
            "tx_id": "test_tx_001",
            "timestamp": 1700000000,
            "origin": "NODE_A",
            "destination": "NODE_B",
            "total_budget": 1000,
            "allocations": {
                "FLOOR_RESERVE": 100,
                "NODE_B": 900
            },
            "hops": ["NODE_A", "NODE_B"]
        }
        ledger_data["transactions"].append(sample_tx)
        engine._atomic_save(ledger_data)

        analyze_mesh_volume()
        captured = capsys.readouterr()
        assert "TORDIAL E8 MESH ROUTING & FEE ANALYTICS" in captured.out
        assert "Total Settled Transactions" in captured.out
    finally:
        ledger_data["transactions"] = original_txs
        engine._atomic_save(ledger_data)
