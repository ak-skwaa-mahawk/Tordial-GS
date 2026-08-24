import math
import asyncio
import json
import logging
import numpy as np
from typing import Dict, Any
from core.mesh.router import SovereignMeshRouter
from core.mesh.e8_tba_solver import E8TBASolver

logger = logging.getLogger("e8_stream")

class E8TelemetryStreamer:
    def __init__(self, node_id: str = "Tordial-GS-Streamer"):
        self.node_id = node_id
        self.router = SovereignMeshRouter(node_id=self.node_id)
        self.tba_solver = E8TBASolver()

    def generate_snapshot_payload(self, T_eff: float = 1.4) -> Dict[str, Any]:
        """Synthesizes active root allocations and TBA equilibrium metrics."""
        tba_data = self.tba_solver.compute_steady_state_queues(T_eff=T_eff)
        
        return {
            "node_id": self.node_id,
            "tba_spectrum": {
                "effective_temp": T_eff,
                "total_queue_load": tba_data["total_queue_load"],
                "vacuum_casimir_energy": tba_data["ground_state_energy"],
                "species_masses": tba_data["species_masses"],
                "queue_depths": tba_data["steady_state_queue_depths"]
            },
            "e8_highways": {
                "active_roots_count": int(np.count_nonzero(self.router.queue_depths > 0.1)),
                "max_congested_depth": float(np.max(self.router.queue_depths)),
                "queue_depths_vector": self.router.queue_depths.tolist()
            }
        }

    async def stream_telemetry_loop(self, iterations: int = 10, interval: float = 0.05):
        """Simulates continuous emission of telemetry frames."""
        for i in range(iterations):
            telemetry_8d = np.array([4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002]) + np.random.normal(0, 0.05, 8)
            self.router.route_burst(telemetry_8d, budget_sats=500)
            
            payload = self.generate_snapshot_payload(T_eff=1.2 + 0.1 * math.sin(i))
            logger.debug(f"[STREAM FRAME {i}]: Active roots={payload['e8_highways']['active_roots_count']}")
            await asyncio.sleep(interval)
        return True
