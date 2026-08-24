import pytest
import math

PI_CORE = 3.1730
PRESSURE = 5.5
GAP = 0.01
MASS_SEAT = 31.316
OVERCLOCK = 1.0417

def audit_signal(incoming_mass: float, phase_shift: float) -> str:
    if incoming_mass < PRESSURE:
        return "WEIGHTLESS_SIGNAL_DETECTED"
    if abs(phase_shift) > GAP:
        return f"RECONSTRUCT_SIGNAL_{PI_CORE}"
    return "SIGNAL_PASSED"

def calculate_signal_density(energy: float) -> float:
    density = (energy * PI_CORE) * OVERCLOCK
    return density + MASS_SEAT

def test_pressure_gate_rejection():
    assert audit_signal(4.2, 0.005) == "WEIGHTLESS_SIGNAL_DETECTED"
    assert audit_signal(5.6, 0.005) == "SIGNAL_PASSED"

def test_phase_shift_reconstruction():
    assert audit_signal(6.0, 0.02) == "RECONSTRUCT_SIGNAL_3.173"
    assert audit_signal(6.0, -0.015) == "RECONSTRUCT_SIGNAL_3.173"
    assert audit_signal(6.0, 0.008) == "SIGNAL_PASSED"

def test_soliton_density_scaling():
    density = calculate_signal_density(10.0)
    expected = (10.0 * PI_CORE) * OVERCLOCK + MASS_SEAT
    assert pytest.approx(density, rel=1e-5) == expected
