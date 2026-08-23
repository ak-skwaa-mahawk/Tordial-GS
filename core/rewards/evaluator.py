"""Long-Horizon Reward & Verification Engine: Replica benchmark evaluation."""
from typing import Dict, Any

class LongHorizonEvaluator:
    def __init__(self, tolerance: float = 1e-4):
        self.tolerance = tolerance

    def score_step_progress(self, current_state: Dict[str, Any], ground_truth: Dict[str, Any]) -> float:
        reward = 0.0
        for key, target_val in ground_truth.items():
            if key in current_state:
                curr_val = current_state[key]
                error = abs(curr_val - target_val)
                if error <= self.tolerance:
                    reward += 1.0
                else:
                    reward += max(0.0, 1.0 - (error / (abs(target_val) + 1e-8)))
        return round(reward, 4)

    def evaluate_terminal_invariants(self, manifold_metrics: Dict[str, float], bounds: Dict[str, tuple]) -> bool:
        for metric, (lower, upper) in bounds.items():
            val = manifold_metrics.get(metric)
            if val is None or not (lower <= val <= upper):
                return False
        return True
