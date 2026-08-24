import pytest
from scripts.continuous_burst_injector import generate_burst_payload

def test_generate_burst_payload_format():
    payload = generate_burst_payload()
    
    assert "queue_size" in payload
    assert "effective_strain" in payload
    assert abs(payload["phase_drift"]) < 0.01  # Must respect phase-lock safety gate
    assert payload["budget_sats"] == 500
