"""Unit tests for continuous mesh health monitor daemon."""

import json
from unittest.mock import patch, MagicMock
from core.mesh.mesh_monitor import MeshMonitor
from core.mesh.crypto_envelope import sign_packet

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
@patch("subprocess.run")
def test_mesh_monitor_run_cycle(mock_run, mock_put):
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
    assert "anomaly_evaluation" in digest

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
@patch("subprocess.run")
def test_mesh_monitor_emits_jitter_alert_on_spike(mock_run, mock_put):
    monitor = MeshMonitor()
    # Baseline history with low jitter (~0.05ms)
    monitor.timeseries.history = [
        {"jitter_ms": 0.048, "mean_delay_ms": 0.5},
        {"jitter_ms": 0.052, "mean_delay_ms": 0.5},
        {"jitter_ms": 0.049, "mean_delay_ms": 0.5},
        {"jitter_ms": 0.051, "mean_delay_ms": 0.5}
    ]

    # Return alternating delays across the 8 carrier roots to induce high jitter (~0.855ms)
    call_idx = {"count": 0}
    def mock_subp(cmd, *args, **kwargs):
        path = cmd[2]
        root_id = int(path.split("_")[-1].split(".")[0])
        raw = {"root_index": root_id, "phase_drift": 0.0, "lyapunov": -6.992}
        delay = 1.8 if (call_idx["count"] % 2 == 0) else 0.2
        call_idx["count"] += 1
        payload = {
            "signed_packet": sign_packet(raw),
            "transit_metrics": {"transit_delay_ms": delay}
        }
        return MagicMock(returncode=0, stdout=json.dumps(payload), stderr="")

    mock_run.side_effect = mock_subp
    mock_put.return_value = {"success": True, "target": "mock_target"}

    digest = monitor.run_cycle()

    assert digest["anomaly_evaluation"]["is_anomaly"] is True
    assert digest["jitter_stats"]["jitter_ms"] > 0.8
    alert_calls = [call for call in mock_put.call_args_list if "telemetry/alerts/jitter_anomaly_" in call[0][0]]
    assert len(alert_calls) == 1
