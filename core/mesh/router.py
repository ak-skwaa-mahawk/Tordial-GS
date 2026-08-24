import math
import logging
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger("mesh_router")

def generate_e8_roots() -> np.ndarray:
    """Generates the 240 root vectors of the E8 Lie algebra."""
    roots = []
    
    # 1. Type D8 roots: (+-1, +-1, 0, 0, 0, 0, 0, 0) and permutations (112 roots)
    for i in range(8):
        for j in range(i + 1, 8):
            for s1 in [1.0, -1.0]:
                for s2 in [1.0, -1.0]:
                    r = np.zeros(8, dtype=float)
                    r[i] = s1
                    r[j] = s2
                    roots.append(r)

    # 2. Type E8 half-integer roots: (+-1/2)^8 with even number of minus signs (128 roots)
    for i in range(256):
        signs = [1.0 if (i >> b) & 1 else -1.0 for b in range(8)]
        if sum(1 for s in signs if s < 0) % 2 == 0:
            roots.append(np.array(signs, dtype=float) * 0.5)

    roots_arr = np.array(roots, dtype=float)
    norms = np.linalg.norm(roots_arr, axis=1, keepdims=True)
    return roots_arr / norms

E8_ROOTS = generate_e8_roots()

class E8RootDispatcher:
    def __init__(self, gamma: float = 0.05, beta_qber: float = 2.0, beta_loss: float = 1.5, qber_crit: float = 0.11):
        self.gamma = gamma
        self.beta_qber = beta_qber
        self.beta_loss = beta_loss
        self.qber_crit = qber_crit
        self.roots = E8_ROOTS

    def compute_dispatch_weights(self, telemetry_8d: np.ndarray, queue_depths: np.ndarray) -> np.ndarray:
        projections = np.dot(self.roots, telemetry_8d)
        base_weights = np.maximum(0.0, projections - (self.gamma * queue_depths))
        
        qber = float(telemetry_8d[2])
        channel_loss = float(telemetry_8d[3])
        
        qber_ratio = max(0.0, qber) / self.qber_crit
        penalty_exponent = (self.beta_qber * (qber_ratio ** 2)) + (self.beta_loss * max(0.0, channel_loss))
        fidelity_attenuation = math.exp(-penalty_exponent)
        
        return base_weights * fidelity_attenuation

class SovereignMeshRouter:
    def __init__(self, node_id: str = "TORDIAL-NODE-01", gamma: float = 0.05):
        self.node_id = node_id
        self.dispatcher = E8RootDispatcher(gamma=gamma)
        self.queue_depths = np.zeros(240, dtype=float)
        self.dispatch_history: List[Dict[str, Any]] = []

    def build_telemetry_vector(
        self,
        queue_size: float = 4.0,
        grad_temp: float = 3.0,
        qber: float = 0.01,
        channel_loss: float = 0.02,
        effective_strain: float = 3.5,
        coherence: float = 0.98,
        entropy: float = 0.2,
        phase_drift: float = 0.002
    ) -> np.ndarray:
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

    def route_burst(self, telemetry_8d: np.ndarray, budget_sats: int = 500) -> Dict[str, Any]:
        mass_norm = float(np.linalg.norm(telemetry_8d))
        phase_drift = float(telemetry_8d[7])
        effective_strain = float(telemetry_8d[4])

        # Gate 1: Phase Drift Tolerance
        if abs(phase_drift) > 0.01:
            logger.warning(f"⚠️ [BURST RESET]: Node={self.node_id} | Reason=PHASE_DRIFT_EXCEEDED | Triggering GLM reconstruct")
            record = {
                "node_id": self.node_id,
                "budget_sats": budget_sats,
                "decision": {
                    "status": "PHASE_DRIFT_GLM_RECONSTRUCT",
                    "phase_drift": phase_drift,
                    "action": "RESET_PHASE_LOCK"
                }
            }
            self.dispatch_history.append(record)
            return record

        # Gate 2: Kinetic Mass Gate
        if mass_norm < 5.5:
            record = {
                "node_id": self.node_id,
                "budget_sats": budget_sats,
                "decision": {
                    "status": "WEIGHTLESS_BURST_CATAPULTED",
                    "mass_norm": mass_norm,
                    "action": "FORWARD_UNPROCESSED"
                }
            }
            self.dispatch_history.append(record)
            return record

        # Gate 3: E8 Optimal Root Highway Projection
        weights = self.dispatcher.compute_dispatch_weights(telemetry_8d, self.queue_depths)
        selected_idx = int(np.argmax(weights))
        selected_weight = float(weights[selected_idx])

        self.queue_depths[selected_idx] += 1.0
        self.queue_depths *= 0.90

        logger.info(
            f"✅ [BURST DISPATCH]: Node={self.node_id} | Root={selected_idx} | "
            f"EffStrain={effective_strain:.1f}% | Weight={selected_weight:.3f} | Budget={budget_sats} sats"
        )

        record = {
            "node_id": self.node_id,
            "budget_sats": budget_sats,
            "decision": {
                "status": "E8_HIGHWAY_DISPATCHED",
                "selected_root_index": selected_idx,
                "dispatch_weight": selected_weight,
                "mass_norm": mass_norm,
                "phase_drift": phase_drift
            }
        }
        self.dispatch_history.append(record)
        return record
