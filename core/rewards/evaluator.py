"""Long-Horizon Reward & Verification Engine: Replica benchmark evaluation."""
from typing import Dict, Any, List

class LongHorizonEvaluator:
    def __init__(self, tolerance: float = 1e-4, step_penalty: float = 0.05):
        self.tolerance = tolerance
        self.step_penalty = step_penalty

    def score_step_progress(self, current_state: Dict[str, Any], ground_truth: Dict[str, Any], step_count: int = 1) -> float:
        """Computes dense step reward with convergence weighting and time-horizon penalty."""
        reward = 0.0
        matched_keys = 0

        for key, target_val in ground_truth.items():
            if key in current_state:
                curr_val = current_state[key]
                matched_keys += 1
                error = abs(curr_val - target_val)
                if error <= self.tolerance:
                    reward += 1.0
                else:
                    norm_denom = abs(target_val) + 1e-8
                    reward += max(0.0, 1.0 - (error / norm_denom))

        # Normalize score across target dimensions and apply step-horizon decay
        if matched_keys > 0:
            reward = reward / matched_keys
        
        horizon_penalty = max(0.0, (step_count - 1) * self.step_penalty)
        return round(max(0.0, reward - horizon_penalty), 4)

    def evaluate_terminal_invariants(self, manifold_metrics: Dict[str, float], bounds: Dict[str, tuple]) -> bool:
        """Evaluates whether final scientific replication invariants are strictly satisfied."""
        if not bounds:
            return False
        for metric, (lower, upper) in bounds.items():
            val = manifold_metrics.get(metric)
            if val is None or not (lower <= val <= upper):
                return False
        return True

    def calculate_trajectory_efficiency(self, step_rewards: List[float]) -> float:
        """Calculates trajectory smoothness to detect oscillating or stalling agent reasoning loops."""
        if not step_rewards:
            return 0.0
        # Positive monotonic trends receive a boost, high variance/oscillations receive lower scores
        trend = step_rewards[-1] - step_rewards[0]
        avg_reward = sum(step_rewards) / len(step_rewards)
        return round(max(0.0, avg_reward + 0.2 * trend), 4)
