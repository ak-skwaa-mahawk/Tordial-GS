import pytest
import numpy as np
from simulations.virtual_headscale_cluster import VirtualHeadscaleMesh
from core.mesh.ledger_settlement import SovereignLedgerEngine

@pytest.mark.asyncio
async def test_node_drop_and_recovery_resilience(tmp_path):
    ledger = SovereignLedgerEngine(ledger_file=tmp_path / "test_drop_ledger.json")
    mesh = VirtualHeadscaleMesh(node_names=["ALPHA", "BETA", "GAMMA"], ledger_engine=ledger)

    # 1. Normal traffic before drop
    storm_before = await mesh.run_traffic_storm(burst_count=6)
    assert storm_before["successful_handoffs"] > 0
    assert storm_before["active_nodes"] == 3

    # 2. Drop node BETA
    mesh.drop_node("BETA")
    assert "BETA" not in mesh.peer_links["ALPHA"]
    assert "BETA" not in mesh.peer_links["GAMMA"]

    # 3. Traffic rerouting with remaining 2 nodes
    storm_during = await mesh.run_traffic_storm(burst_count=6)
    assert storm_during["active_nodes"] == 2
    assert storm_during["successful_handoffs"] > 0

    # 4. Recover node BETA
    mesh.recover_node("BETA")
    assert "BETA" in mesh.peer_links["ALPHA"]
    storm_after = await mesh.run_traffic_storm(burst_count=6)
    assert storm_after["active_nodes"] == 3

@pytest.mark.asyncio
async def test_degraded_link_handling(tmp_path):
    ledger = SovereignLedgerEngine(ledger_file=tmp_path / "test_degrade_ledger.json")
    mesh = VirtualHeadscaleMesh(node_names=["NODE-A", "NODE-B"], ledger_engine=ledger)

    # Inject severe degradation on link A -> B
    mesh.degrade_link("NODE-A", "NODE-B")
    
    telemetry = np.array([4.5, 3.2, 0.01, 0.01, 3.5, 0.99, 0.1, 0.001])
    res = await mesh.forward_burst_packet(origin_node="NODE-A", telemetry_8d=telemetry, ttl=2)

    # The burst should complete hop 1, adjust telemetry upon degradation, and settle
    assert res["origin"] == "NODE-A"
    assert res["total_hops"] == 2
    assert res["settlement"]["status"] == "SETTLED"
