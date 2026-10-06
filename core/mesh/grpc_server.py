"""SovereignMeshService gRPC Server.

Exposes SovereignMeshRouter dispatch and settlement queries over network sockets,
with real-time peer telemetry tracking and geodesic peer routing selection.
"""

import time
import threading
from concurrent import futures

import grpc
import numpy as np

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

PEER_TTL_SECONDS = 120.0


class SovereignMeshServicer(router_pb2_grpc.SovereignMeshServiceServicer):
    def __init__(self, node_id: str = "EDGE-GRPC-01"):
        self.node_id = node_id
        self.router = SovereignMeshRouter(node_id=node_id)
        self._lock = threading.Lock()
        self.peer_registry = {}

    def _update_and_select_peer(self, origin_node_id: str, telemetry: np.ndarray, root_index: int, dispatch_weight: float) -> str:
        now = time.time()
        with self._lock:
            if origin_node_id:
                self.peer_registry[origin_node_id] = {
                    "telemetry": telemetry,
                    "root_index": root_index,
                    "weight": dispatch_weight,
                    "last_seen": now,
                }

            stale_peers = [p for p, data in self.peer_registry.items() if (now - data["last_seen"]) > PEER_TTL_SECONDS]
            for p in stale_peers:
                del self.peer_registry[p]

            candidates = [
                (peer_id, data)
                for peer_id, data in self.peer_registry.items()
                if peer_id != origin_node_id
            ]

            if not candidates:
                return f"E8-EGRESS-ROOT-{root_index:02d}"

            best_peer = None
            best_cost = float("inf")

            for peer_id, data in candidates:
                root_delta = abs(data["root_index"] - root_index)
                tel_dist = np.linalg.norm(telemetry - data["telemetry"])
                score = (root_delta * 0.4) + (tel_dist * 0.6) + abs(data["weight"] - dispatch_weight) * 0.1
                if score < best_cost:
                    best_cost = score
                    best_peer = peer_id

            return best_peer or f"E8-EGRESS-ROOT-{root_index:02d}"

    def _process_route_burst(self, request):
        t0 = time.perf_counter_ns()

        tel = request.telemetry
        if tel:
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
        else:
            telemetry_array = np.zeros(8, dtype=float)

        raw_result = self.router.route_burst(telemetry_array, budget_sats=request.budget_sats)
        decision_data = raw_result.get("decision", {})

        raw_status = decision_data.get("status", "")
        if raw_status in STATUS_MAP:
            status_enum = STATUS_MAP[raw_status]
        elif any(k in raw_status for k in ["REJECT", "RESET", "DRIFT", "GATE"]):
            status_enum = router_pb2.PRESSURE_GATE_REJECTED
        else:
            status_enum = router_pb2.DISPATCH_STATUS_UNSPECIFIED

        selected_root = int(decision_data.get("selected_root_index", 0))
        dispatch_wt = float(decision_data.get("dispatch_weight", 0.0))

        target_peer = self._update_and_select_peer(
            origin_node_id=request.origin_node_id,
            telemetry=telemetry_array,
            root_index=selected_root,
            dispatch_weight=dispatch_wt,
        )

        decision = router_pb2.RouteDecision(
            status=status_enum,
            selected_root_index=selected_root,
            dispatch_weight=dispatch_wt,
            mass_norm=float(decision_data.get("mass_norm", 0.0)),
            phase_drift=float(decision_data.get("phase_drift", 0.0)),
            target_peer_id=target_peer,
        )

        t_elapsed_ns = time.perf_counter_ns() - t0

        return router_pb2.RouteBurstResponse(
            node_id=self.node_id,
            budget_sats=request.budget_sats,
            allocations=[],
            decision=decision,
            settled_balance_status="OK",
            process_duration_ns=t_elapsed_ns,
        )

    def RouteBurst(self, request, context):
        return self._process_route_burst(request)

    def StreamRouteBursts(self, request_iterator, context):
        for request in request_iterator:
            yield self._process_route_burst(request)

    def UpdateTelemetry(self, request, context):
        tel = request.telemetry
        if tel:
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
        else:
            telemetry_array = np.zeros(8, dtype=float)

        if hasattr(self.router, "update_peer_telemetry"):
            self.router.update_peer_telemetry(request.node_id, telemetry_array)

        with self._lock:
            if request.node_id:
                self.peer_registry[request.node_id] = {
                    "telemetry": telemetry_array,
                    "root_index": 0,
                    "weight": 0.0,
                    "last_seen": time.time(),
                }

        seq = getattr(self.router, "current_sequence", 1)
        return router_pb2.TelemetryUpdateResponse(
            accepted=True,
            current_sequence=int(seq),
        )

    def GetSettlementStatus(self, request, context):
        tx_id = request.tx_id
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
                settlement_status=str(record.get("settlement_status", "CONFIRMED")),
            )
            return router_pb2.SettlementStatusResponse(
                record=pb_record,
                is_certified=True,
                journal_root_hash=str(record.get("root_hash", "0x0")),
            )

        return router_pb2.SettlementStatusResponse(
            record=router_pb2.SettlementJournalRecord(
                tx_id=tx_id,
                settlement_status="NOT_FOUND",
            ),
            is_certified=False,
            journal_root_hash="",
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
    srv = serve()
    try:
        srv.wait_for_termination()
    except KeyboardInterrupt:
        srv.stop(0)
