"""Unit tests for TUI telemetry dashboard."""

from unittest.mock import patch, MagicMock
from core.mesh.mesh_tui_dashboard import render_dashboard, run_loop

@patch("subprocess.run")
@patch("core.mesh.mesh_tui_dashboard.probe_vault_health")
@patch("os.system")
def test_render_dashboard_nominal(mock_sys, mock_probe, mock_subp):
    mock_probe.return_value = {
        "status": "HEALTHY",
        "latency_ms": 150.0,
        "free_bytes": 1024**3 * 500
    }
    mock_subp.return_value = MagicMock(returncode=1, stdout="", stderr="")

    # Verify execution without unhandled exceptions
    render_dashboard()
    mock_probe.assert_called_once()

@patch("core.mesh.mesh_tui_dashboard.render_dashboard")
@patch("time.sleep")
def test_run_loop_bounded(mock_sleep, mock_render):
    run_loop(interval_sec=0.01, max_ticks=2)
    assert mock_render.call_count == 2
    assert mock_sleep.call_count == 1
