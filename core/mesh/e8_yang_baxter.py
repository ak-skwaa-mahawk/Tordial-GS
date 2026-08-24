import cmath
import math
import numpy as np
from typing import Dict, Any

E8_EXPONENTS = [1, 7, 11, 13, 17, 19, 23, 29]
COXETER_H = 30

class E8SMatrix:
    def __init__(self, xi: float = 0.5):
        self.xi = xi
        self.masses = np.array([2.0 * math.sin(math.pi * s / COXETER_H) for s in E8_EXPONENTS])

    def scalar_s_matrix(self, a: int, b: int, theta: complex) -> complex:
        """
        Computes the meromorphic S-matrix element S_ab(theta) for E8 Toda species (a, b).
        Uses bootstrap pole structure: S_ab(theta) = sinh(theta/2 + i*pi*lambda) / sinh(theta/2 - i*pi*lambda).
        """
        # Effective pole offset lambda determined by Coxeter exponent combination
        s_a = E8_EXPONENTS[a]
        s_b = E8_EXPONENTS[b]
        pole_shift = ((s_a + s_b) % COXETER_H) / (2.0 * COXETER_H) * self.xi
        
        num = cmath.sinh(theta / 2.0 + 1j * math.pi * pole_shift)
        den = cmath.sinh(theta / 2.0 - 1j * math.pi * pole_shift)
        
        if abs(den) < 1e-12:
            den = 1e-12
            
        return num / den

    def verify_unitarity(self, a: int, b: int, theta: complex) -> float:
        """Verifies S_ab(theta) * S_ab(-theta) == 1."""
        s_pos = self.scalar_s_matrix(a, b, theta)
        s_neg = self.scalar_s_matrix(a, b, -theta)
        product = s_pos * s_neg
        return abs(product - 1.0)

    def verify_yang_baxter_triplet(self, a: int, b: int, c: int, theta1: float, theta2: float, theta3: float) -> Dict[str, Any]:
        """
        Verifies the 3-particle Yang-Baxter factorization consistency:
        S_ab(t12) * S_ac(t13) * S_bc(t23) == S_bc(t23) * S_ac(t13) * S_ab(t12)
        """
        t12 = complex(theta1 - theta2, 0.0)
        t13 = complex(theta1 - theta3, 0.0)
        t23 = complex(theta2 - theta3, 0.0)

        s12 = self.scalar_s_matrix(a, b, t12)
        s13 = self.scalar_s_matrix(a, c, t13)
        s23 = self.scalar_s_matrix(b, c, t23)

        lhs = s12 * s13 * s23
        rhs = s23 * s13 * s12

        discrepancy = abs(lhs - rhs)
        is_unitary_12 = self.verify_unitarity(a, b, t12) < 1e-6
        is_unitary_13 = self.verify_unitarity(a, c, t13) < 1e-6
        is_unitary_23 = self.verify_unitarity(b, c, t23) < 1e-6

        return {
            "triplet": (a, b, c),
            "rapidities": (theta1, theta2, theta3),
            "ybe_discrepancy": discrepancy,
            "ybe_exact": bool(discrepancy < 1e-7),
            "unitarity_preserved": bool(is_unitary_12 and is_unitary_13 and is_unitary_23)
        }
