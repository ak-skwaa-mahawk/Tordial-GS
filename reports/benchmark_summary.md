# Tordial-GS: Replica Benchmark Performance Report

**Generated:** `2026-08-23T05:23:36.774351+00:00`  
**Orchestrator Engine:** `Tordial-GS Scientific Director`  
**Aggregate Pass Rate:** `100.0%` (3/3 tasks)  
**Mean Trajectory Efficiency:** `0.89`

---

## Domain Task Breakdown

| Task ID | Domain | Invariant Parameters | Efficiency | Status |
| :--- | :--- | :--- | :--- | :--- |
| `REP_PHYS_001` | classical_physics | damping_ratio, natural_freq_rad_s, decay_constant | `0.89` | **PASSED** |
| `REP_BIO_002` | structural_biology | phi_angle_deg, psi_angle_deg, clash_score | `0.89` | **PASSED** |
| `REP_MAT_003` | materials_science | goldschmidt_tolerance, octahedral_tilt_deg, bandgap_ev | `0.89` | **PASSED** |

---

## Detailed Trajectory Logs

### `REP_PHYS_001` - Classical Physics
> Estimate damping ratio and natural frequency for underdamped harmonic oscillator.

* **Tolerance Bound:** `0.001`
* **Max Allotted Steps:** `5`
* **Step Rewards:** `[0.7, 0.95, 0.9]`
* **Terminal State:** `PASSED`

### `REP_BIO_002` - Structural Biology
> Validate alpha-helix backbone dihedral angles (phi, psi) and steric clash score.

* **Tolerance Bound:** `0.05`
* **Max Allotted Steps:** `4`
* **Step Rewards:** `[0.7, 0.95, 0.9]`
* **Terminal State:** `PASSED`

### `REP_MAT_003` - Materials Science
> Compute Goldschmidt tolerance factor and octahedral tilt distortion in cubic perovskite.

* **Tolerance Bound:** `0.01`
* **Max Allotted Steps:** `4`
* **Step Rewards:** `[0.7, 0.95, 0.9]`
* **Terminal State:** `PASSED`
