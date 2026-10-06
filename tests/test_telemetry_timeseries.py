"""Unit tests for telemetry time-series rolling history and cold hydration."""

import json
from unittest.mock import patch, MagicMock
from core.mesh.telemetry_timeseries import TelemetryTimeSeries

@patch("subprocess.run")
@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
def test_append_sample_and_rolling_limit(mock_put, mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
    mock_put.return_value = {"success": True, "target": "mock_target"}

    ts = TelemetryTimeSeries(hydrate=False)
    sample = {
        "timestamp": 1700000000.0,
        "jitter_stats": {
            "mean_delay_ms": 0.52,
            "jitter_ms": 0.08,
            "min_delay_ms": 0.40,
            "max_delay_ms": 0.65
        },
        "all_healthy": True,
        "monitored_roots_count": 8
    }

    res = ts.append_sample(sample)
    assert res["window_size"] == 1
    assert res["samples"][0]["mean_delay_ms"] == 0.52
    assert res["samples"][0]["all_healthy"] is True
    assert mock_put.call_count == 1

@patch("subprocess.run")
def test_hydrate_from_vault(mock_run):
    payload = {
        "samples": [
            {"timestamp": 1.0, "jitter_ms": 0.08},
            {"timestamp": 2.0, "jitter_ms": 0.09}
        ]
    }
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(payload), stderr="")

    ts = TelemetryTimeSeries(hydrate=True)
    assert len(ts.history) == 2
    assert ts.history[0]["jitter_ms"] == 0.08
