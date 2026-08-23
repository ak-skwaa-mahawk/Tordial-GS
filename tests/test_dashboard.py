import pytest
import json
from scripts.live_dashboard import TelemetryDashboard

def test_dashboard_packet_processing():
    dash = TelemetryDashboard()
    
    sample_step_packet = json.dumps({
        "type": "experiment_step",
        "payload": {
            "plan_id": "TEST-PLAN-001",
            "node_id": "H1_test",
            "step": 1,
            "reward": 0.85
        }
    }).encode("utf-8")
    
    dash.process_packet(sample_step_packet)
    assert dash.packet_count == 1
    assert "TEST-PLAN-001" in dash.active_plans
    assert dash.active_plans["TEST-PLAN-001"]["node_id"] == "H1_test"
    assert dash.active_plans["TEST-PLAN-001"]["reward"] == 0.85

def test_dashboard_summary_packet_processing():
    dash = TelemetryDashboard()
    summary_packet = json.dumps({
        "type": "experiment_summary",
        "payload": {
            "plan_id": "TEST-PLAN-001",
            "status": "SUCCESS",
            "efficiency": 0.92
        }
    }).encode("utf-8")
    
    dash.process_packet(summary_packet)
    assert dash.active_plans["TEST-PLAN-001"]["status"] == "SUCCESS"
