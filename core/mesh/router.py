import time
import logging
import numpy as np
from typing import Dict, Any, Optional
from core.mesh.e8_root_dispatcher import E8RootDispatcher

logger = logging.getLogger("mesh_router")

class SovereignMeshRouter:
    def __init__(self, node_id: str = "NODE-01", pressure_gate: float = 5.5, gap_tolerance: float = 0.01):
        self.node_id = node_id
        self.dispatcher = E8RootDispatcher(pressure_gate=pressure_gate, gap_tolerance=gap_tolerance)
        self.queue_depths = np.zeros(240, dtype=float)
        self.dispatch_history = []

    def build_telemetry_vector(
        self,
        queue_size: float,
        grad_temp: float,
        qber: float,
        channel_loss: float,
        effective_strain: float,
        coherence: float,
        entropy: float,
        phase_drift: float
    ) -> np.ndarray:
        """Packs scalar network metrics into an 8D state vector."""
        return np.array([
            queue_size,
            grad_temp,
            qber,
            channel_loss,
            effective_strain,
            coherence,
            entropy,
            phase_drift
        ], dtype=float)

    def route_burst(
        self,
        telemetry_8d: np.ndarray,
        budget_sats: int = 500
    ) -> Dict[str, Any]:
        """Evaluates 8D state against the 240 E8 root highways and dispatches."""
        decision = self.dispatcher.select_optimal_burst_highway(
            telemetry_8d,
            queue_depths=self.queue_depths
        )
        
        root_idx = decision["selected_root_index"]
        status = decision["status"]
        
        if status == "E8_HIGHWAY_DISPATCHED":
            # Increment congestion counter on the chosen root highway
            self.queue_depths[root_idx] += 1.0
            eff_strain = float(telemetry_8d[4]) if len(telemetry_8d) > 4 else 0.0
            
            logger.info(
                f"✅ [BURST DISPATCH]: Node={self.node_id} | Root={root_idx} | "
                f"EffStrain={eff_strain:.1f}% | Weight={decision['dispatch_weight']:.3f} | Budget={budget_sats} sats"
            )
        elif status == "WEIGHTLESS_BURST_CATAPULTED":
            logger.warning(
                f"⚠️ [BURST REJECTED]: Node={self.node_id} | Reason=PRESSURE_GATE | Mass={decision['incoming_mass']:.2f}"
            )
        elif status == "PHASE_DRIFT_GLM_RECONSTRUCT":
            logger.warning(
                f"⚠️ [BURST RESET]: Node={self.node_id} | Reason=PHASE_DRIFT_EXCEEDED | Triggering GLM reconstruct"
            )

        # Decay global queue depths to model continuous egress
        self.queue_depths = np.maximum(0.0, self.queue_depths - 0.1)
        
        record = {
            "timestamp": time.time(),
            "node_id": self.node_id,
            "budget_sats": budget_sats,
            "decision": decision
        }
        self.dispatch_history.append(record)
        return record
