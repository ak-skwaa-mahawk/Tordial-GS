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
    "PHASE_DRIFT_GLM_RECONSTRUCT": router_pb2.PRESSURE_GATE_REJECTED,
    "PHASE_DRIFT_EXCEEDED": router_pb2.PRESSURE_GATE_REJECTED,
    "BURST_RESET": router_pb2.PRESSURE_GATE_REJECTED,
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

        raw_status = decision_data.get("status", "")
        if raw_status in STATUS_MAP:
            status_enum = STATUS_MAP[raw_status]
        elif any(k in raw_status for k in ["REJECT", "RESET", "DRIFT", "GATE"]):
            status_enum = router_pb2.PRESSURE_GATE_REJECTED
        else:
            status_enum = router_pb2.DISPATCH_STATUS_UNSPECIFIED

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

    def StreamRouteBursts(self, request_iterator, context):
        """
        Bidirectional streaming RPC handler for continuous high-rate telemetry pipelines.
        Yields a RouteBurstResponse immediately for every ingested RouteBurstRequest frame.
        """
        for request in request_iterator:
            yield self.RouteBurst(request, context)

    def UpdateTelemetry(self, request, context):
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
        
        # Ingest into router state tracking
        if hasattr(self.router, "update_peer_telemetry"):
            self.router.update_peer_telemetry(request.node_id, telemetry_array)

        seq = getattr(self.router, "current_sequence", 1)
        return router_pb2.TelemetryUpdateResponse(
            accepted=True,
            current_sequence=int(seq)
        )

    def GetSettlementStatus(self, request, context):
        tx_id = request.tx_id
        # Query router or ledger settlement records
        ledger = getattr(self.router, "ledger", None)
        record = None
        if ledger and hasattr(ledger, "get_transaction"):
            record = ledger.get_transaction(tx_id)

        if record:
            pb_record = router_pb2.SettlementJournalRecord(
                tx_id=str(record.get("tx_id", tx_id)),
                timestamp_epoch=int(record.get("timestamp_epoch", 0)),
                origin_node=str(record.get("origin_node", "")),
                hop_count=int(record.get("hop_count", 0)),
                route_hops=list(record.get("route_hops", [])),
                total_budget_sats=int(record.get("total_budget_sats", 0)),
                node_payout_sats=int(record.get("node_payout_sats", 0)),
                floor_reserve_sats=int(record.get("floor_reserve_sats", 0)),
                xrpl_tx_hash=str(record.get("xrpl_tx_hash", "")),
                settlement_status=str(record.get("settlement_status", "CONFIRMED"))
            )
            return router_pb2.SettlementStatusResponse(
                record=pb_record,
                is_certified=True,
                journal_root_hash=str(record.get("root_hash", "0x0"))
            )

        # Default fallback response for non-existent or un-flushed tx
        return router_pb2.SettlementStatusResponse(
            record=router_pb2.SettlementJournalRecord(
                tx_id=tx_id,
                settlement_status="NOT_FOUND"
            ),
            is_certified=False,
            journal_root_hash=""
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
