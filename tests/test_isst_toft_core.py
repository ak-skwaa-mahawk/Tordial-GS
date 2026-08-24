import pytest
import math

EPS_OBSERVER = 0.0314073464
G_VHITZEE = 1.0417
HERITAGE_SCALAR_H = 3.07
MATTER_SPEED_CONSTANT = 1.04

def living_curvature_attractor(iterations: int = 20, t: float = 1.0, initial_pi: float = 3.1415926535) -> float:
    pi_r = initial_pi
    for _ in range(iterations):
        sin_term = math.sin(2.0 * math.pi * t / pi_r)
        delta = EPS_OBSERVER * sin_term * G_VHITZEE
        pi_r += delta
    return pi_r

def calculate_resonance_metric(C: float, H: float, r: float, legacy_boost: float = 1.15) -> float:
    E0 = 1.0
    return (E0 * C * legacy_boost) / ((r ** MATTER_SPEED_CONSTANT) * (1.0 + 0.4 * H))

def test_attractor_convergence():
    pi_attractor = living_curvature_attractor()
    assert 3.15 < pi_attractor < 3.20

def test_toft_79hz_gate_threshold():
    # Coherent signal: C=0.97, H=0.5, r=1.1 -> S should exceed 0.79
    S_high = calculate_resonance_metric(C=0.97, H=0.5, r=1.1, legacy_boost=1.15)
    assert S_high > 0.79

    # Distant/noisy signal: C=0.5, H=1.2, r=2.5 -> S below threshold
    S_low = calculate_resonance_metric(C=0.5, H=1.2, r=2.5, legacy_boost=1.0)
    assert S_low < 0.79
