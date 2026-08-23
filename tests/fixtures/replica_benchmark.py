"""Replica Benchmark Synthetic Test Fixtures:
Simulates multi-domain scientific replication challenges (Physics Parameter Estimation,
Structural Biology Envelopes, and Material Phase Invariants).
"""
from dataclasses import dataclass
from typing import Dict, Tuple, Any

@dataclass
class ReplicaTask:
    task_id: str
    domain: str
    description: str
    ground_truth: Dict[str, float]
    invariant_bounds: Dict[str, Tuple[float, float]]
    max_steps: int
    tolerance: float

REPLICA_BENCHMARK_TASKS: Dict[str, ReplicaTask] = {
    "REP_PHYS_001_DAMPED_OSCILLATION": ReplicaTask(
        task_id="REP_PHYS_001",
        domain="classical_physics",
        description="Estimate damping ratio and natural frequency for underdamped harmonic oscillator.",
        ground_truth={
            "damping_ratio": 0.125,
            "natural_freq_rad_s": 4.712,
            "decay_constant": 0.589
        },
        invariant_bounds={
            "damping_ratio": (0.120, 0.130),
            "natural_freq_rad_s": (4.65, 4.75),
            "decay_constant": (0.58, 0.60)
        },
        max_steps=5,
        tolerance=1e-3
    ),
    "REP_BIO_002_RAMACHANDRAN_ENVELOPE": ReplicaTask(
        task_id="REP_BIO_002",
        domain="structural_biology",
        description="Validate alpha-helix backbone dihedral angles (phi, psi) and steric clash score.",
        ground_truth={
            "phi_angle_deg": -57.0,
            "psi_angle_deg": -47.0,
            "clash_score": 0.015
        },
        invariant_bounds={
            "phi_angle_deg": (-62.0, -52.0),
            "psi_angle_deg": (-52.0, -42.0),
            "clash_score": (0.0, 0.03)
        },
        max_steps=4,
        tolerance=5e-2
    ),
    "REP_MAT_003_PEROVSKITE_TOLERANCE": ReplicaTask(
        task_id="REP_MAT_003",
        domain="materials_science",
        description="Compute Goldschmidt tolerance factor and octahedral tilt distortion in cubic perovskite.",
        ground_truth={
            "goldschmidt_tolerance": 0.952,
            "octahedral_tilt_deg": 1.45,
            "bandgap_ev": 1.62
        },
        invariant_bounds={
            "goldschmidt_tolerance": (0.94, 0.96),
            "octahedral_tilt_deg": (1.35, 1.55),
            "bandgap_ev": (1.58, 1.66)
        },
        max_steps=4,
        tolerance=1e-2
    )
}

def get_task(task_id_or_domain: str) -> ReplicaTask:
    """Retrieve fixture task by exact ID or key name."""
    if task_id_or_domain in REPLICA_BENCHMARK_TASKS:
        return REPLICA_BENCHMARK_TASKS[task_id_or_domain]
    for task in REPLICA_BENCHMARK_TASKS.values():
        if task.task_id == task_id_or_domain or task.domain == task_id_or_domain:
            return task
    raise KeyError(f"Task '{task_id_or_domain}' not found in Replica fixtures.")
