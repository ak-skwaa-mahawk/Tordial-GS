import pytest
import time
import numpy as np
from core.mesh.failover_router import DynamicFailoverMeshRouter

def test_peer_heartbeat_expiration_and_fallback():
    router = DynamicFailoverMeshRouter(node_id="TORDIAL-EDGE-01", failure_threshold_sec=0.2)
    assert len(router.get_healthy_peers()) == 6

    # Wait for heartbeat threshold to expire
    time.sleep(0.25)
    healthy = router.get_healthy_peers()
    assert len(healthy) == 0

    # Route burst during total peer disconnect
    vec = router.build_telemetry_vector(4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002)
    record = router.route_burst_with_failover(vec, budget_sats=500)
    assert record["decision"]["failover_mode"] == "LOCAL_FALLBACK"
    assert record["decision"]["active_healthy_peers"] == 0

    # Heartbeat restored for selected node
    router.record_peer_heartbeat("GAMMA")
    assert "GAMMA" in router.get_healthy_peers()
    
    recovered_record = router.route_burst_with_failover(vec, budget_sats=500)
    assert recovered_record["decision"]["failover_mode"] == "DISTRIBUTED"
    assert recovered_record["decision"]["active_healthy_peers"] == 1
