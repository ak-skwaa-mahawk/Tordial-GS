import pytest
import numpy as np
from core.mesh.router import SovereignMeshRouter

def test_router_dispatch_lifecycle():
    router = SovereignMeshRouter(node_id="TEST-NODE-01")
    
    # State with norm > 5.5 and low phase drift (< 0.01)
    telemetry = router.build_telemetry_vector(
        queue_size=4.0,
        grad_temp=3.0,
        qber=0.02,
        channel_loss=0.01,
        effective_strain=3.5,
        coherence=0.99,
        entropy=0.15,
        phase_drift=0.002
    )
    
    record = router.route_burst(telemetry, budget_sats=500)
    decision = record["decision"]
    
    assert decision["status"] == "E8_HIGHWAY_DISPATCHED"
    assert 0 <= decision["selected_root_index"] < 240
    assert len(router.dispatch_history) == 1
    
    # Verify congestion decay applied
    chosen_root = decision["selected_root_index"]
    assert router.queue_depths[chosen_root] == pytest.approx(0.9, rel=1e-3)

def test_router_pressure_gate_rejection():
    router = SovereignMeshRouter(node_id="TEST-NODE-01")
    
    # Low mass vector (norm < 5.5)
    weak_telemetry = router.build_telemetry_vector(
        queue_size=0.1,
        grad_temp=0.1,
        qber=0.0,
        channel_loss=0.0,
        effective_strain=0.1,
        coherence=0.5,
        entropy=0.1,
        phase_drift=0.0
    )
    
    record = router.route_burst(weak_telemetry, budget_sats=100)
    assert record["decision"]["status"] == "WEIGHTLESS_BURST_CATAPULTED"
