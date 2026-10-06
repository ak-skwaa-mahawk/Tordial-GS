"""Unit tests for E8 polytope generator."""

import pytest
from core.mesh.e8_polytope import generate_e8_roots, get_root_vector

def test_root_count_and_norm():
    roots = generate_e8_roots()
    assert len(roots) == 240
    # Every root in standard E8 normalization has squared Euclidean length = 2.0
    for r in roots:
        squared_norm = sum(x**2 for x in r)
        assert pytest.approx(squared_norm, rel=1e-5) == 2.0

def test_root_indexing_bounds():
    r0 = get_root_vector(0)
    assert len(r0) == 8
    r239 = get_root_vector(239)
    assert len(r239) == 8
    with pytest.raises(ValueError):
        get_root_vector(240)
