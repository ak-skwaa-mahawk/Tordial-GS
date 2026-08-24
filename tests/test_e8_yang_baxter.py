import pytest
import numpy as np
from core.mesh.e8_yang_baxter import E8SMatrix

def test_e8_s_matrix_unitarity():
    s_matrix = E8SMatrix(xi=0.5)
    
    # Test unitarity across random rapidity differences
    for theta_val in [0.5, 1.2, -0.8, 2.4]:
        theta = complex(theta_val, 0.0)
        for a in range(8):
            for b in range(8):
                err = s_matrix.verify_unitarity(a, b, theta)
                assert err == pytest.approx(0.0, abs=1e-5)

def test_yang_baxter_factorization():
    s_matrix = E8SMatrix(xi=0.5)
    
    # Test various 3-particle species combinations and rapidities
    res = s_matrix.verify_yang_baxter_triplet(
        a=0, b=2, c=5,
        theta1=1.8, theta2=0.6, theta3=-0.4
    )
    
    assert res["ybe_exact"] is True
    assert res["unitarity_preserved"] is True
    assert res["ybe_discrepancy"] < 1e-7

def test_yang_baxter_all_species():
    s_matrix = E8SMatrix(xi=0.5)
    
    # Run test on extreme species modes (lightest species 0, intermediate 3, heaviest 7)
    res = s_matrix.verify_yang_baxter_triplet(
        a=0, b=3, c=7,
        theta1=2.5, theta2=1.0, theta3=-1.2
    )
    assert res["ybe_exact"] is True
    assert res["unitarity_preserved"] is True
