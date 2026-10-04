# Empirical Ground Truth Benchmark Specifications

The `ReplicaTask` architecture evaluates autonomous reasoning agents against non-arbitrary physical invariants.

## 1. Classical Physics: Underdamped Harmonic Oscillator
Governing Differential Equation:
$$\ddot{x} + 2\zeta\omega_n\dot{x} + \omega_n^2x = 0$$

- **Natural Frequency ($\omega_n$):** 4.712 rad/s (Tolerance: 4.65 - 4.75)
- **Damping Ratio ($\zeta$):** 0.125 (Tolerance: 0.120 - 0.130)
- **Decay Constant ($\gamma = \zeta\omega_n$):** 0.589 s^-1 (Tolerance: 0.58 - 0.60)

## 2. Structural Biology: Polypeptide Dihedral Angles
Validates steric exclusion boundaries in (phi, psi) phase space (Ramachandran criterion) preventing atomic overlap in alpha-helices and beta-sheets.

## 3. Materials Science: Goldschmidt Tolerance Factor
Goldschmidt factor for ABX_3 perovskite crystal stability:
$$t = \frac{r_A + r_X}{\sqrt{2}(r_B + r_X)}$$

Stable cubic lattice invariant requirement: 0.8 <= t <= 1.0.
