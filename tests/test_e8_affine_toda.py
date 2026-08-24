import pytest
import math
import numpy as np

# E8 Coxeter exponents and Coxeter number
E8_EXPONENTS = [1, 7, 11, 13, 17, 19, 23, 29]
COXETER_H = 30

def get_e8_cartan_matrix() -> np.ndarray:
    C = np.array([
        [ 2, -1,  0,  0,  0,  0,  0,  0],
        [-1,  2, -1,  0,  0,  0,  0,  0],
        [ 0, -1,  2, -1,  0,  0,  0,  0],
        [ 0,  0, -1,  2, -1,  0,  0,  0],
        [ 0,  0,  0, -1,  2, -1,  0, -1],
        [ 0,  0,  0,  0, -1,  2, -1,  0],
        [ 0,  0,  0,  0,  0, -1,  2,  0],
        [ 0,  0,  0,  0, -1,  0,  0,  2]
    ], dtype=float)
    return C

def calculate_e8_toda_masses(m0: float = 1.0) -> np.ndarray:
    return np.array([2.0 * m0 * math.sin(math.pi * s / COXETER_H) for s in E8_EXPONENTS])

def test_e8_cartan_properties():
    C = get_e8_cartan_matrix()
    # Rank = 8
    assert C.shape == (8, 8)
    # Symmetric (simply-laced Lie algebra)
    assert np.allclose(C, C.T)
    # Determinant of standard E8 Cartan is exactly 1 (unimodular lattice)
    det_C = int(round(np.linalg.det(C)))
    assert det_C == 1

def test_e8_toda_mass_spectrum():
    masses = calculate_e8_toda_masses(m0=1.0)
    assert len(masses) == 8
    # Lowest mass mode (s=1): m1 = 2 * sin(pi/30) ~ 0.209057
    assert pytest.approx(masses[0], rel=1e-5) == 2.0 * math.sin(math.pi / 30.0)
    # Highest mass mode (s=29): identical to s=1 by reflection symmetry
    assert pytest.approx(masses[-1], rel=1e-5) == 2.0 * math.sin(29.0 * math.pi / 30.0)
    assert pytest.approx(masses[0], rel=1e-5) == masses[-1]

def test_e8_affine_charge_parity():
    # Affine parity rule: sum(soliton_types % 2) must be 0 for topological neutrality
    soliton_types_neutral = np.array([2, 4, 6, 8])
    total_charge = float(np.sum(soliton_types_neutral % 2))
    assert bool(abs(total_charge) <= 1e-9) is True

    soliton_types_charged = np.array([1, 2, 4, 6])
    total_charge_unbalanced = float(np.sum(soliton_types_charged % 2))
    assert bool(abs(total_charge_unbalanced) <= 1e-9) is False
