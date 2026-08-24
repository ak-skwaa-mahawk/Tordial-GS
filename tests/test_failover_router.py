import pytest
import time
import numpy as np
from core.mesh.failover_router import DynamicFailoverMeshRouter

def test_failover_router_healthy_state():
    router = DynamicFailoverMeshRouter(failure_threshold_sec=5.0)
    assert len(router.get_healthy_peers()) == 6
    
    vec = router.build_telemetry_vector(4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002)
    res = router.route_burst_with_failover(vec, budget_sats=500)
    assert res["decision"]["failover_mode"] == "DISTRIBUTED"
    assert res["decision"]["active_healthy_peers"] == 6

def test_failover_peer_timeout_penalty():
    router = DynamicFailoverMeshRouter(failure_threshold_sec=0.1)
    time.sleep(0.15)
    
    healthy = router.get_healthy_peers()
    assert len(healthy) == 0
    assert router.peer_penalty_multipliers["ALPHA"] > 1.0
    
    # Heartbeat recovery
    router.record_peer_heartbeat("ALPHA")
    assert "ALPHA" in router.get_healthy_peers()
    assert router.peer_penalty_multipliers["ALPHA"] == 1.0
