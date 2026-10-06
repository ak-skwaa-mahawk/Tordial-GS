#!/usr/bin/env python3
"""
SovereignMeshService gRPC server implementation.
Exposes SovereignMeshRouter dispatch and settlement queries over network sockets.
"""
import time
import numpy as np
import grpc
from concurrent import futures

from core.mesh import router_pb2, router_pb2_grpc
from core.mesh.router import SovereignMeshRouter

STATUS_MAP = {
    "E8_HIGHWAY_DISPATCHED": router_pb2.E8_HIGHWAY_DISPATCHED,
    "PRESSURE_GATE_REJECTED": router_pb2.PRESSURE_GATE_REJECTED,
    "THERMAL_THROTTLE_HELD": router_pb2.THERMAL_THROTTLE_HELD,
    "INSUFFICIENT_BUDGET": router_pb2.INSUFFICIENT_BUDGET,
    "TOPOLOGICAL_FAULT": router_pb2.TOPOLOGICAL_FAULT,
}

class SovereignMeshServicer(router_pb2_grpc.SovereignMeshServiceServicer):
    def __init__(self, node_id: str = "EDGE-GRPC-01"):
        self.node_id = node_id
        self.router = SovereignMeshRouter(node_id=node_id)

    def RouteBurst(self, request, context):
        t0 = time.perf_counter_ns()

        # Unpack 8D telemetry vector
        tel = request.telemetry
        telemetry_array = np.array([
            tel.latency_ms,
            tel.queue_depth,
            tel.thermal_headroom,
            tel.battery_reserve,
            tel.packet_loss_rate,
            tel.bandwidth_capacity,
            tel.memory_pressure,
            tel.compute_load,
        ], dtype=float)

        # Execute routing pass
        raw_result = self.router.route_burst(telemetry_array, budget_sats=request.budget_sats)
        decision_data = raw_result.get("decision", {})

        status_enum = STATUS_MAP.get(
            decision_data.get("status", ""),
            router_pb2.DISPATCH_STATUS_UNSPECIFIED
        )

        decision = router_pb2.RouteDecision(
            status=status_enum,
            selected_root_index=int(decision_data.get("selected_root_index", 0)),
            dispatch_weight=float(decision_data.get("dispatch_weight", 0.0)),
            mass_norm=float(decision_data.get("mass_norm", 0.0)),
            phase_drift=float(decision_data.get("phase_drift", 0.0)),
            target_peer_id=str(decision_data.get("target_peer_id", ""))
        )

        t_elapsed_ns = time.perf_counter_ns() - t0

        return router_pb2.RouteBurstResponse(
            node_id=raw_result.get("node_id", self.node_id),
            budget_sats=raw_result.get("budget_sats", request.budget_sats),
            decision=decision,
            settled_balance_status="OK",
            process_duration_ns=t_elapsed_ns
        )

def serve(host: str = "127.0.0.1", port: int = 50055):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    router_pb2_grpc.add_SovereignMeshServiceServicer_to_server(
        SovereignMeshServicer(), server
    )
    bind_addr = f"{host}:{port}"
    server.add_insecure_port(bind_addr)
    server.start()
    print(f"[*] SovereignMeshService gRPC listening on {bind_addr}")
    return server

if __name__ == "__main__":
    server = serve()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
