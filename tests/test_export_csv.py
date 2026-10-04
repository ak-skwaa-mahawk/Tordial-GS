import csv
from pathlib import Path
from scripts.export_ledger_csv import export_ledger_to_csv
from core.mesh.ledger_settlement import SovereignLedgerEngine

def test_export_ledger_csv(tmp_path):
    engine = SovereignLedgerEngine()
    ledger_data = engine.load_ledger()
    original_txs = list(ledger_data.get("transactions", []))
    
    try:
        sample_tx = {
            "tx_id": "test_tx_export_001",
            "timestamp": 1700000000,
            "sender": "ALICE",
            "destination": "BOB",
            "volume_sats": 5000,
            "root_type": "E8_ROOT_PRIMARY",
            "fee_sats": 25
        }
        ledger_data["transactions"].append(sample_tx)
        engine._atomic_save(ledger_data)

        target_csv = tmp_path / "test_report.csv"
        res = export_ledger_to_csv(output_path=target_csv)

        assert res.exists()
        with open(res, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) > 0
    finally:
        ledger_data["transactions"] = original_txs
        engine._atomic_save(ledger_data)
