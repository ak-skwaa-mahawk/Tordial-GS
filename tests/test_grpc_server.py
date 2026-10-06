import pytest
import grpc
from concurrent import futures
from core.mesh import router_pb2, router_pb2_grpc
from core.mesh.grpc_server import SovereignMeshServicer

@pytest.fixture(scope="module")
def grpc_channel():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    router_pb2_grpc.add_SovereignMeshServiceServicer_to_server(
        SovereignMeshServicer(node_id="TEST-NODE"), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    yield channel

    server.stop(None)
    channel.close()

def test_grpc_route_burst(grpc_channel):
    stub = router_pb2_grpc.SovereignMeshServiceStub(grpc_channel)
    telemetry = router_pb2.TelemetryVector(
        latency_ms=4.0,
        queue_depth=3.0,
        thermal_headroom=0.01,
        battery_reserve=0.02,
        packet_loss_rate=3.5,
        bandwidth_capacity=0.98,
        memory_pressure=0.2,
        compute_load=0.002
    )
    req = router_pb2.RouteBurstRequest(
        origin_node_id="ORIGIN-A",
        telemetry=telemetry,
        budget_sats=500
    )

    resp = stub.RouteBurst(req)
    assert resp.node_id == "TEST-NODE"
    assert resp.budget_sats == 500
    assert resp.decision.status == router_pb2.E8_HIGHWAY_DISPATCHED
    assert resp.decision.selected_root_index >= 0
    assert resp.process_duration_ns > 0

def test_grpc_stream_route_bursts(grpc_channel):
    stub = router_pb2_grpc.SovereignMeshServiceStub(grpc_channel)

    def generate_requests(count=10):
        for i in range(count):
            telemetry = router_pb2.TelemetryVector(
                latency_ms=4.0 + (i * 0.01),
                queue_depth=3.0,
                thermal_headroom=0.01,
                battery_reserve=0.02,
                packet_loss_rate=3.5,
                bandwidth_capacity=0.98,
                memory_pressure=0.2,
                compute_load=0.002
            )
            yield router_pb2.RouteBurstRequest(
                origin_node_id=f"STREAM-CLIENT-{i}",
                telemetry=telemetry,
                budget_sats=500
            )

    responses = list(stub.StreamRouteBursts(generate_requests(10)))
    assert len(responses) == 10
    for resp in responses:
        assert resp.decision.status == router_pb2.E8_HIGHWAY_DISPATCHED
        assert resp.decision.selected_root_index >= 0
        assert resp.process_duration_ns > 0

def test_grpc_update_telemetry(grpc_channel):
    stub = router_pb2_grpc.SovereignMeshServiceStub(grpc_channel)
    telemetry = router_pb2.TelemetryVector(
        latency_ms=3.2,
        queue_depth=1.0,
        thermal_headroom=0.01,
        battery_reserve=0.95,
        packet_loss_rate=0.001,
        bandwidth_capacity=0.99,
        memory_pressure=0.15,
        compute_load=0.001
    )
    req = router_pb2.TelemetryUpdateRequest(
        node_id="PEER-EDGE-09",
        telemetry=telemetry,
        timestamp_epoch_ms=1700000000000
    )
    resp = stub.UpdateTelemetry(req)
    assert resp.accepted is True
    assert resp.current_sequence >= 0

def test_grpc_get_settlement_status(grpc_channel):
    stub = router_pb2_grpc.SovereignMeshServiceStub(grpc_channel)
    req = router_pb2.SettlementStatusRequest(tx_id="tx_test_mesh_01")
    resp = stub.GetSettlementStatus(req)
    assert resp.record.tx_id == "tx_test_mesh_01"
    assert resp.record.settlement_status in ["NOT_FOUND", "CONFIRMED"]
