"""Scientific Director Orchestrator: Maps experimental hypotheses, DAG topologies,
dynamic recovery, branch pruning, and deadlock detection.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

@dataclass
class ExperimentNode:
    node_id: str
    hypothesis: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, RUNNING, VERIFIED, FAILED, RETRYING, PRUNED
    result_metrics: Optional[Dict[str, float]] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0

class ScientificDirector:
    def __init__(self, plan_id: str, max_retries: int = 2, min_efficiency_threshold: float = 0.25):
        self.plan_id = plan_id
        self.max_retries = max_retries
        self.min_efficiency_threshold = min_efficiency_threshold
        self.nodes: Dict[str, ExperimentNode] = {}

    def add_step(self, node_id: str, hypothesis: str, parameters: Dict[str, Any], dependencies: List[str] = None):
        deps = dependencies or []
        self.nodes[node_id] = ExperimentNode(
            node_id=node_id,
            hypothesis=hypothesis,
            parameters=parameters,
            dependencies=deps
        )

    def get_executable_nodes(self) -> List[ExperimentNode]:
        ready = []
        for node in self.nodes.values():
            if node.status == "PENDING":
                if all(self.nodes[dep].status == "VERIFIED" for dep in node.dependencies if dep in self.nodes):
                    ready.append(node)
        return ready

    def record_outcome(self, node_id: str, status: str, metrics: Optional[Dict[str, float]] = None, error: Optional[str] = None):
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]
        if status == "FAILED":
            if node.retry_count < self.max_retries:
                node.status = "RETRYING"
                node.retry_count += 1
                node.failure_reason = error
                diag_id = f"{node_id}_diag_{node.retry_count}"
                self.add_step(
                    node_id=diag_id,
                    hypothesis=f"Diagnostic isolation for {node_id}: {error or 'Unknown failure'}",
                    parameters={"target_node": node_id, "retry_attempt": node.retry_count},
                    dependencies=[dep for dep in node.dependencies]
                )
                node.dependencies.append(diag_id)
                node.status = "PENDING"
            else:
                node.status = "FAILED"
                node.failure_reason = error
                self.prune_downstream_branches(node_id)
        else:
            node.status = status
            node.result_metrics = metrics

    def prune_downstream_branches(self, failed_node_id: str) -> List[str]:
        """Recursively cascades PRUNED status to all downstream dependent nodes."""
        pruned_nodes = []
        
        def find_and_prune(parent_id: str):
            for n_id, n_obj in self.nodes.items():
                if parent_id in n_obj.dependencies and n_obj.status not in ("VERIFIED", "PRUNED"):
                    n_obj.status = "PRUNED"
                    n_obj.failure_reason = f"Pruned: Upstream dependency '{parent_id}' failed or stalled"
                    pruned_nodes.append(n_id)
                    find_and_prune(n_id)

        find_and_prune(failed_node_id)
        return pruned_nodes

    def prune_stalled_branches_by_efficiency(self, current_efficiency: float) -> List[str]:
        """Prunes currently retrying or low-confidence branches if global trajectory efficiency collapses."""
        if current_efficiency >= self.min_efficiency_threshold:
            return []

        pruned = []
        for node_id, node in list(self.nodes.items()):
            if node.status in ("RETRYING", "PENDING") and node.retry_count > 0:
                node.status = "PRUNED"
                node.failure_reason = f"Pruned due to low trajectory efficiency ({current_efficiency:.3f} < {self.min_efficiency_threshold})"
                pruned.append(node_id)
                pruned.extend(self.prune_downstream_branches(node_id))
        return list(set(pruned))

    def detect_deadlock(self) -> Dict[str, Any]:
        """Detects whether execution is completely stalled due to blocked dependencies, cycles, or all-pruned paths."""
        executable = self.get_executable_nodes()
        pending_nodes = [n for n in self.nodes.values() if n.status in ("PENDING", "RUNNING", "RETRYING")]
        
        is_cyclic = self.has_circular_dependencies()
        is_deadlocked = len(pending_nodes) > 0 and len(executable) == 0

        return {
            "is_deadlocked": is_deadlocked or is_cyclic,
            "has_cycles": is_cyclic,
            "blocked_nodes": [n.node_id for n in pending_nodes] if is_deadlocked else [],
            "reason": "Circular dependency detected" if is_cyclic else ("Dependency exhaustion / pruned ancestors" if is_deadlocked else "OK")
        }

    def has_circular_dependencies(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def is_cyclic(v: str) -> bool:
            visited.add(v)
            rec_stack.add(v)
            for neighbor in self.nodes[v].dependencies:
                if neighbor not in visited:
                    if neighbor in self.nodes and is_cyclic(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(v)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if is_cyclic(node_id):
                    return True
        return False
