import json
from scripts.analyze_mesh_volume import analyze_mesh_volume
from core.mesh.ledger_settlement import SovereignLedgerEngine

def test_analyze_mesh_volume(capsys):
    # Ensure ledger has at least one transaction for analytics output
    engine = SovereignLedgerEngine()
    ledger_data = engine.load_ledger()
    original_txs = list(ledger_data.get("transactions", []))
    
    try:
        sample_tx = {
            "tx_id": "test_tx_001",
            "timestamp": 1700000000,
            "sender": "ALICE",
            "destination": "BOB",
            "volume_sats": 1000,
            "root_type": "E8_ROOT_A",
            "fee_sats": 10
        }
        ledger_data["transactions"].append(sample_tx)
        engine._atomic_save(ledger_data)

        analyze_mesh_volume()
        captured = capsys.readouterr()
        assert "TORDIAL E8 MESH ROUTING & FEE ANALYTICS" in captured.out
    finally:
        ledger_data["transactions"] = original_txs
        engine._atomic_save(ledger_data)
