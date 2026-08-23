"""Scientific Director Orchestrator: Maps experimental hypotheses, DAG topologies, and dynamic recovery."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

@dataclass
class ExperimentNode:
    node_id: str
    hypothesis: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, RUNNING, VERIFIED, FAILED, RETRYING
    result_metrics: Optional[Dict[str, float]] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0

class ScientificDirector:
    def __init__(self, plan_id: str, max_retries: int = 2):
        self.plan_id = plan_id
        self.max_retries = max_retries
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
                if all(self.nodes[dep].status == "VERIFIED" for dep in node.dependencies):
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
                # Insert dynamic diagnostic step before retrying
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
        else:
            node.status = status
            node.result_metrics = metrics

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
