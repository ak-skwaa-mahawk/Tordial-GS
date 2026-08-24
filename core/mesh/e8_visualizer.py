import math
import numpy as np
from typing import Dict, Any, List
from core.mesh.e8_tba_solver import E8TBASolver

class E8TerminalVisualizer:
    def __init__(self, solver: E8TBASolver = None):
        self.solver = solver or E8TBASolver()

    def render_e8_heat_grid(self, queue_depths: np.ndarray) -> str:
        """
        Renders 240 E8 roots as a 15x16 terminal density grid.
        Shades: . (idle) -> ░ -> ▒ -> ▓ -> █ (congested)
        """
        assert len(queue_depths) == 240, "Queue depths must have 240 elements"
        
        # Density ramp
        RAMP = ["\033[90m.\033[0m", "\033[36m░\033[0m", "\033[32m▒\033[0m", "\033[33m▓\033[0m", "\033[31;1m█\033[0m"]
        max_q = max(float(np.max(queue_depths)), 1.0)
        
        lines = ["\033[1;37m=== 240 E8 ROOT HIGHWAY ALLOCATION MAP (15x16) ===\033[0m"]
        for row in range(15):
            row_str = "  "
            for col in range(16):
                idx = row * 16 + col
                val = queue_depths[idx]
                level = min(int((val / max_q) * 4), 4)
                row_str += f"{RAMP[level]} "
            lines.append(row_str)
        return "\n".join(lines)

    def render_tba_queue_spectrum(self, T_eff: float = 1.0) -> str:
        """
        Renders horizontal bar charts of the 8 TBA equilibrium queue modes.
        """
        data = self.solver.compute_steady_state_queues(T_eff=T_eff)
        depths = data["steady_state_queue_depths"]
        masses = data["species_masses"]
        
        max_depth = max(depths) if depths else 1.0
        lines = [
            f"\033[1;37m=== TBA STEADY-STATE QUEUE SPECTRUM (T_eff={T_eff:.2f}, Load={data['total_queue_load']:.3f}) ===\033[0m"
        ]
        
        for a in range(8):
            q_val = depths[a]
            bar_len = int((q_val / max_depth) * 24)
            bar = "\033[34m█\033[0m" * bar_len
            lines.append(
                f"  Species {a+1} [m={masses[a]:.3f}]: {bar:<24} \033[32m{q_val:.4f}\033[0m"
            )
            
        lines.append(f"  \033[90mVacuum Casimir Energy: {data['ground_state_energy']:.4f}\033[0m")
        return "\n".join(lines)

    def render_full_dashboard(self, queue_depths: np.ndarray, T_eff: float = 1.0) -> str:
        grid = self.render_e8_heat_grid(queue_depths)
        spectrum = self.render_tba_queue_spectrum(T_eff)
        return f"\n{grid}\n\n{spectrum}\n"
