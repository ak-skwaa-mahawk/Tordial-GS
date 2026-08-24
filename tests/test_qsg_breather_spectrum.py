import pytest
import math
import numpy as np

def calculate_breather_mass(n: int, xi: float = 0.5, M: float = 1.0) -> float:
    return 2.0 * M * math.sin(n * math.pi * xi / 2.0)

def guard_topological_charge(state: np.ndarray) -> bool:
    charge = float(np.sum(np.sign(state)))
    return bool(abs(charge) <= 1e-9)

def test_breather_mass_quantization():
    M = 1.0
    xi = 0.5
    # n=1 fundamental breather: m_1 = sqrt(2) * M
    m1 = calculate_breather_mass(1, xi, M)
    assert pytest.approx(m1, rel=1e-5) == math.sqrt(2.0) * M

    # n=2 breather: m_2 = 2 * M * sin(pi/2) = 2.0 * M
    m2 = calculate_breather_mass(2, xi, M)
    assert pytest.approx(m2, rel=1e-5) == 2.0 * M

def test_topological_charge_guard():
    # Balanced kink-antikink pair (charge = 0)
    neutral_state = np.array([1.0, 0.8, -0.8, -1.0])
    assert guard_topological_charge(neutral_state) is True

    # Unbalanced rogue excitation (charge = +2)
    charged_state = np.array([1.0, 0.5, 0.2, -0.1])
    assert guard_topological_charge(charged_state) is False
