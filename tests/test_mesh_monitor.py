"""Unit tests for continuous mesh health monitor daemon."""

import json
from unittest.mock import patch, MagicMock
from core.mesh.mesh_monitor import MeshMonitor
from core.mesh.crypto_envelope import sign_packet

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
@patch("subprocess.run")
def test_mesh_monitor_run_cycle(mock_run, mock_put):
    # Construct authentic HMAC-signed packet payload
    raw_payload = {
        "root_index": 0,
        "phase_drift": 0.0,
        "lyapunov": -6.992
    }
    mock_payload = {
        "signed_packet": sign_packet(raw_payload),
        "transit_metrics": {
            "transit_delay_ms": 0.55
        }
    }
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_payload), stderr="")
    mock_put.return_value = {"success": True, "target": "mock_target"}

    monitor = MeshMonitor()
    digest = monitor.run_cycle()

    assert digest["monitored_roots_count"] == 8
    assert digest["jitter_stats"]["sample_count"] == 8
    assert digest["jitter_stats"]["mean_delay_ms"] == 0.55
    assert digest["all_healthy"] is True
