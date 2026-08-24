import pytest
import numpy as np
from core.mesh.e8_tba_solver import E8TBASolver

def test_tba_solver_convergence():
    solver = E8TBASolver(m0=1.0, num_points=24, theta_max=2.5)
    eps = solver.solve_pseudo_energies(T_eff=1.5, max_iter=30)
    
    assert eps.shape == (8, 24)
    # Pseudo-energies must be symmetric: eps(theta) == eps(-theta)
    for a in range(8):
        assert np.allclose(eps[a], eps[a][::-1], atol=1e-4)

def test_tba_queue_distribution_monotonicity():
    solver = E8TBASolver(m0=1.0, num_points=24, theta_max=2.5)
    
    # Higher temperature (higher entropy) leads to higher queue occupation
    q_cold = solver.compute_steady_state_queues(T_eff=0.5)
    q_hot = solver.compute_steady_state_queues(T_eff=2.0)
    
    assert q_hot["total_queue_load"] > q_cold["total_queue_load"]
    assert len(q_cold["steady_state_queue_depths"]) == 8
