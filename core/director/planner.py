"""Scientific Director Orchestrator: Maps experimental hypotheses and DAG topologies."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ExperimentNode:
    node_id: str
    hypothesis: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = "PENDING"
    result_metrics: Optional[Dict[str, float]] = None

class ScientificDirector:
    def __init__(self, plan_id: str):
        self.plan_id = plan_id
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

    def record_outcome(self, node_id: str, status: str, metrics: Dict[str, float]):
        if node_id in self.nodes:
            self.nodes[node_id].status = status
            self.nodes[node_id].result_metrics = metrics
