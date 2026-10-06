"""Unit tests for telemetry time-series rolling history."""

from unittest.mock import patch
from core.mesh.telemetry_timeseries import TelemetryTimeSeries

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
def test_append_sample_and_rolling_limit(mock_put):
    mock_put.return_value = {"success": True, "target": "mock_target"}

    ts = TelemetryTimeSeries()
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
