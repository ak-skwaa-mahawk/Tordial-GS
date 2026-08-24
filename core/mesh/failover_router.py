import time
import numpy as np
from typing import Dict, List, Optional
from core.mesh.router import SovereignMeshRouter

class DynamicFailoverMeshRouter(SovereignMeshRouter):
    def __init__(self, node_id: str = "TORDIAL-EDGE-01", failure_threshold_sec: float = 30.0):
        super().__init__(node_id=node_id)
        self.failure_threshold_sec = failure_threshold_sec
        self.peer_heartbeats: Dict[str, float] = {
            "HEADSCALE-ALPHA": time.time(),
            "HEADSCALE-BETA": time.time(),
            "HEADSCALE-GAMMA": time.time(),
            "ALPHA": time.time(),
            "BETA": time.time(),
            "GAMMA": time.time(),
        }
        self.peer_penalty_multipliers: Dict[str, float] = {k: 1.0 for k in self.peer_heartbeats}

    def record_peer_heartbeat(self, peer_id: str):
        self.peer_heartbeats[peer_id] = time.time()
        self.peer_penalty_multipliers[peer_id] = 1.0

    def get_healthy_peers(self) -> List[str]:
        now = time.time()
        healthy = []
        for peer, last_seen in self.peer_heartbeats.items():
            if now - last_seen < self.failure_threshold_sec:
                healthy.append(peer)
            else:
                # Exponential backoff cost penalty
                self.peer_penalty_multipliers[peer] = min(10.0, self.peer_penalty_multipliers[peer] * 1.5)
        return healthy

    def route_burst_with_failover(self, telemetry_8d: np.ndarray, budget_sats: int = 500) -> Dict:
        healthy_peers = self.get_healthy_peers()
        record = self.route_burst(telemetry_8d, budget_sats=budget_sats)

        # Annotate failover status
        record["decision"]["active_healthy_peers"] = len(healthy_peers)
        record["decision"]["failover_mode"] = "LOCAL_FALLBACK" if not healthy_peers else "DISTRIBUTED"
        return record
