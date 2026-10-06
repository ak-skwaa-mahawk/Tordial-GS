"""Unit tests for vault watchdog probe."""

import json
from unittest.mock import patch, MagicMock
from core.mesh.vault_watchdog import probe_vault_health

@patch("subprocess.run")
def test_probe_vault_healthy(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({"total": 1000000000, "used": 500000, "free": 999500000}),
        stderr=""
    )
    res = probe_vault_health()
    assert res["status"] == "HEALTHY"
    assert res["free_bytes"] == 999500000
    assert "latency_ms" in res

@patch("subprocess.run")
def test_probe_vault_unreachable(mock_run):
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Failed to make oauth client"
    )
    res = probe_vault_health()
    assert res["status"] == "UNREACHABLE"
    assert "oauth client" in res["error"]
