import math
import numpy as np
from itertools import combinations, product
from typing import List, Dict, Any

class E8RootDispatcher:
    def __init__(self, pressure_gate: float = 5.5, gap_tolerance: float = 0.01):
        self.pressure_gate = pressure_gate
        self.gap_tolerance = gap_tolerance
        self.roots = self._generate_240_e8_roots()
        
    def _generate_240_e8_roots(self) -> np.ndarray:
        roots = []
        
        # 1. Type D8 roots (112 vectors): (+-1, +-1, 0, 0, 0, 0, 0, 0) permutations
        for i, j in combinations(range(8), 2):
            for s1, s2 in product([-1.0, 1.0], repeat=2):
                vec = np.zeros(8, dtype=float)
                vec[i] = s1
                vec[j] = s2
                roots.append(vec)
                
        # 2. Type E8 half-integer roots (128 vectors): (+-1/2, ..., +-1/2) with even sum
        for signs in product([-0.5, 0.5], repeat=8):
            if sum(1 for s in signs if s < 0) % 2 == 0:
                roots.append(np.array(signs, dtype=float))
                
        roots_arr = np.array(roots, dtype=float)
        assert roots_arr.shape == (240, 8), f"Expected 240 roots, got {roots_arr.shape[0]}"
        return roots_arr

    def compute_dispatch_weights(self, telemetry_8d: np.ndarray, queue_depths: np.ndarray = None) -> np.ndarray:
        """
        Projects an 8D node state vector onto all 240 E8 root highways.
        telemetry_8d: [Q, grad_T, QBER, Loss, Strain, Coherence, Entropy, PhaseDrift]
        """
        if queue_depths is None:
            queue_depths = np.zeros(240, dtype=float)
            
        norm = np.linalg.norm(telemetry_8d)
        if norm < 1e-9:
            return np.zeros(240, dtype=float)
            
        unit_telemetry = telemetry_8d / norm
        projections = np.dot(self.roots, unit_telemetry)
        weights = np.maximum(0.0, projections - (queue_depths * 0.05))
        return weights

    def select_optimal_burst_highway(self, telemetry_8d: np.ndarray, queue_depths: np.ndarray = None) -> Dict[str, Any]:
        weights = self.compute_dispatch_weights(telemetry_8d, queue_depths)
        best_root_idx = int(np.argmax(weights))
        best_weight = float(weights[best_root_idx])
        
        incoming_mass = float(np.linalg.norm(telemetry_8d))
        phase_drift = float(telemetry_8d[7]) if len(telemetry_8d) > 7 else 0.0
        
        if incoming_mass < self.pressure_gate:
            status = "WEIGHTLESS_BURST_CATAPULTED"
        elif abs(phase_drift) > self.gap_tolerance:
            status = "PHASE_DRIFT_GLM_RECONSTRUCT"
        else:
            status = "E8_HIGHWAY_DISPATCHED"
            
        return {
            "selected_root_index": best_root_idx,
            "root_vector": self.roots[best_root_idx].tolist(),
            "dispatch_weight": round(best_weight, 4),
            "incoming_mass": round(incoming_mass, 4),
            "status": status
        }
