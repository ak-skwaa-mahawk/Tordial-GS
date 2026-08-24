import math
import numpy as np
from typing import Dict, Any

E8_EXPONENTS = [1, 7, 11, 13, 17, 19, 23, 29]
COXETER_H = 30

class E8TBASolver:
    def __init__(self, m0: float = 1.0, L: float = 1.0, num_points: int = 32, theta_max: float = 3.0):
        self.m0 = m0
        self.L = L
        self.theta_max = theta_max
        self.num_points = num_points
        self.theta_grid = np.linspace(-theta_max, theta_max, num_points)
        self.d_theta = self.theta_grid[1] - self.theta_grid[0]
        
        # 8 mass eigenvalues for E8
        self.masses = np.array([2.0 * m0 * math.sin(math.pi * s / COXETER_H) for s in E8_EXPONENTS])
        self.cartan_matrix = self._init_cartan()

    def _init_cartan(self) -> np.ndarray:
        return np.array([
            [ 2, -1,  0,  0,  0,  0,  0,  0],
            [-1,  2, -1,  0,  0,  0,  0,  0],
            [ 0, -1,  2, -1,  0,  0,  0,  0],
            [ 0,  0, -1,  2, -1,  0,  0,  0],
            [ 0,  0,  0, -1,  2, -1,  0, -1],
            [ 0,  0,  0,  0, -1,  2, -1,  0],
            [ 0,  0,  0,  0,  0, -1,  2,  0],
            [ 0,  0,  0,  0, -1,  0,  0,  2]
        ], dtype=float)

    def solve_pseudo_energies(self, T_eff: float = 1.0, max_iter: int = 50, tol: float = 1e-5) -> np.ndarray:
        """
        Solves the coupled non-linear integral equations for epsilon_a(theta) via successive approximations.
        Returns array of shape (8, num_points).
        """
        N = self.num_points
        # Initial guess: asymptotic free term epsilon_a^0(theta) = (m_a * L / T_eff) * cosh(theta)
        eps = np.zeros((8, N), dtype=float)
        cosh_theta = np.cosh(self.theta_grid)
        
        for a in range(8):
            eps[a] = (self.masses[a] * self.L / T_eff) * cosh_theta

        # Iterative convolution kernel update
        for _ in range(max_iter):
            eps_old = eps.copy()
            ln_terms = np.log1p(np.exp(-np.clip(eps, -50.0, 50.0)))
            
            for a in range(8):
                free_term = (self.masses[a] * self.L / T_eff) * cosh_theta
                kernel_sum = np.zeros(N, dtype=float)
                
                for b in range(8):
                    if a != b and self.cartan_matrix[a, b] != 0:
                        # Coupled phase kernel approximated by discrete rapid convolution
                        kernel_weight = abs(self.cartan_matrix[a, b]) / (2.0 * math.pi)
                        kernel_sum += kernel_weight * ln_terms[b] * self.d_theta
                        
                eps[a] = free_term - kernel_sum

            if np.max(np.abs(eps - eps_old)) < tol:
                break

        return eps

    def compute_steady_state_queues(self, T_eff: float = 1.0) -> Dict[str, Any]:
        """Calculates occupation probabilities and steady-state queue depths across the 8 species."""
        eps = self.solve_pseudo_energies(T_eff=T_eff)
        occupations = 1.0 / (1.0 + np.exp(np.clip(eps, -50.0, 50.0)))
        
        # Integrate occupation fraction over rapidity space
        queue_depths = np.sum(occupations, axis=1) * self.d_theta
        
        # Central charge estimation (ground state vacuum Casimir energy)
        ground_state_energy = - (T_eff / (2.0 * math.pi)) * np.sum(
            np.array([self.masses[a] * np.sum(occupations[a] * np.cosh(self.theta_grid)) * self.d_theta for a in range(8)])
        )

        return {
            "effective_temp": T_eff,
            "species_masses": self.masses.tolist(),
            "steady_state_queue_depths": queue_depths.tolist(),
            "total_queue_load": float(np.sum(queue_depths)),
            "ground_state_energy": float(ground_state_energy)
        }
