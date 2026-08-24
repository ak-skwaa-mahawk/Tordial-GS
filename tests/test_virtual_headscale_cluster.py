import pytest
import numpy as np
from simulations.virtual_headscale_cluster import VirtualHeadscaleMesh
from core.mesh.ledger_settlement import SovereignLedgerEngine

@pytest.mark.asyncio
async def test_virtual_headscale_mesh_traffic_storm(tmp_path):
    ledger = SovereignLedgerEngine(ledger_file=tmp_path / "test_mesh_ledger.json")
    mesh = VirtualHeadscaleMesh(node_names=["ALPHA", "BETA", "GAMMA"], ledger_engine=ledger)
    
    summary = await mesh.run_traffic_storm(burst_count=15)
    
    assert summary["nodes_in_mesh"] == 3
    assert summary["bursts_injected"] == 15
    assert summary["successful_handoffs"] > 0
    assert summary["total_settled_transactions"] == summary["successful_handoffs"]

@pytest.mark.asyncio
async def test_virtual_headscale_single_handoff_and_settlement(tmp_path):
    ledger = SovereignLedgerEngine(ledger_file=tmp_path / "test_handoff_ledger.json")
    mesh = VirtualHeadscaleMesh(node_names=["NODE-A", "NODE-B"], ledger_engine=ledger)
    
    telemetry = np.array([4.5, 3.2, 0.01, 0.01, 3.5, 0.99, 0.1, 0.001])
    res = await mesh.forward_burst_packet(origin_node="NODE-A", telemetry_8d=telemetry, ttl=2)
    
    assert res["origin"] == "NODE-A"
    assert res["total_hops"] == 2
    assert res["final_status"] == "E8_HIGHWAY_DISPATCHED"
    assert res["settlement"]["status"] == "SETTLED"
    assert "NODE-A" in res["settlement"]["allocations"]
    assert "NODE-B" in res["settlement"]["allocations"]
    assert "FLOOR_RESERVE" in res["settlement"]["allocations"]
