import pytest
import numpy as np
from core.mesh.e8_root_dispatcher import E8RootDispatcher

def test_e8_root_geometry_invariants():
    dispatcher = E8RootDispatcher()
    roots = dispatcher.roots
    
    # Check root count and dimensionality
    assert roots.shape == (240, 8)
    
    # Every root in E8 must have squared norm = 2.0
    norms_sq = np.sum(roots ** 2, axis=1)
    assert np.allclose(norms_sq, 2.0)
    
    # Check 112 integral roots vs 128 half-integral roots
    is_half_int = np.all(np.abs(np.abs(roots) - 0.5) < 1e-6, axis=1)
    assert np.sum(is_half_int) == 128
    assert np.sum(~is_half_int) == 112

def test_e8_dispatch_selection():
    dispatcher = E8RootDispatcher(pressure_gate=5.5, gap_tolerance=0.01)
    
    # High-energy coherent state with norm >= 5.5: sqrt(4^2 + 3^2 + 3^2 + ...) > 5.8
    telemetry_state = np.array([4.0, 3.0, 0.1, 0.05, 3.0, 0.98, 0.2, 0.003])
    res = dispatcher.select_optimal_burst_highway(telemetry_state)
    
    assert res["status"] == "E8_HIGHWAY_DISPATCHED"
    assert res["dispatch_weight"] > 0.0
    assert 0 <= res["selected_root_index"] < 240

def test_e8_kinetic_pressure_and_phase_gates():
    dispatcher = E8RootDispatcher(pressure_gate=5.5, gap_tolerance=0.01)
    
    # 1. Low mass state -> rejected by pressure gate (norm ~ 0.53 < 5.5)
    weak_state = np.array([0.1, 0.1, 0.0, 0.0, 0.1, 0.5, 0.1, 0.0])
    res_weak = dispatcher.select_optimal_burst_highway(weak_state)
    assert res_weak["status"] == "WEIGHTLESS_BURST_CATAPULTED"
    
    # 2. High mass (norm ~ 6.0 > 5.5) but phase drift (0.05 > 0.01) -> triggers GLM reconstruct
    drifting_state = np.array([4.0, 3.0, 0.1, 0.0, 3.5, 0.9, 0.1, 0.05])
    res_drift = dispatcher.select_optimal_burst_highway(drifting_state)
    assert res_drift["status"] == "PHASE_DRIFT_GLM_RECONSTRUCT"
