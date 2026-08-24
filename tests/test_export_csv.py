import pytest
import csv
from pathlib import Path
from scripts.export_ledger_csv import export_ledger_to_csv

def test_export_ledger_csv(tmp_path):
    target_csv = tmp_path / "test_report.csv"
    res = export_ledger_to_csv(output_path=target_csv)
    
    assert res.exists()
    with open(res, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) > 0
        assert "tx_id" in rows[0]
        assert "total_budget_sats" in rows[0]
        assert "floor_reserve_sats" in rows[0]
