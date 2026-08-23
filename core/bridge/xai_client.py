import json
import asyncio
from typing import Dict, Any, List, Optional
from core.director.planner import ScientificDirector
from core.bridge.worker_pool import WorkerBridge

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scientific_director_plan",
            "description": "Register a new hypothesis and experiment node in the execution DAG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Unique identifier for this plan sequence."},
                    "node_id": {"type": "string", "description": "Unique identifier for this experiment node."},
                    "hypothesis": {"type": "string", "description": "Description of the scientific hypothesis to test."},
                    "parameters": {"type": "object", "description": "Parameters governing this experimental step."},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of node_ids that must complete before this node can run."
                    }
                },
                "required": ["node_id", "hypothesis"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sandbox_execute",
            "description": "Execute isolated Python simulation or verification code inside the sandboxed environment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Identifier for the execution task."},
                    "code": {"type": "string", "description": "Executable Python code. Must output __METRICS__=<json> for telemetry extraction."}
                },
                "required": ["task_id", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trajectory_status",
            "description": "Inspect the status, dependency graph, and deadlock state of a plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan identifier to inspect."}
                },
                "required": ["plan_id"]
            }
        }
    }
]

class XAIBridgeEngine:
    def __init__(self, default_timeout: float = 10.0, max_concurrency: int = 4):
        self.directors: Dict[str, ScientificDirector] = {}
        self.bridge = WorkerBridge(max_concurrency=max_concurrency, sandbox_timeout=default_timeout)

    def get_or_create_director(self, plan_id: str) -> ScientificDirector:
        if plan_id not in self.directors:
            self.directors[plan_id] = ScientificDirector(plan_id=plan_id)
        return self.directors[plan_id]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "scientific_director_plan":
            plan_id = arguments.get("plan_id", "DEFAULT_PLAN")
            director = self.get_or_create_director(plan_id)
            node_id = arguments["node_id"]
            hypothesis = arguments.get("hypothesis", "")
            parameters = arguments.get("parameters", {})
            dependencies = arguments.get("dependencies", [])
            node = director.add_step(node_id=node_id, hypothesis=hypothesis, parameters=parameters, dependencies=dependencies)
            node = director.nodes[node_id]
            executable_node_ids = [n.node_id for n in director.get_executable_nodes()]
            return {
                "status": "NODE_REGISTERED",
                "plan_id": plan_id,
                "node_id": arguments["node_id"],
                "hypothesis": arguments["hypothesis"],
                "dependencies": arguments.get("dependencies", []),
                "hypothesis": node.hypothesis,
                "dependencies": node.dependencies,
                "executable_now": node.node_id in executable_node_ids
            }
        elif tool_name == "sandbox_execute":
            task_id = arguments.get("task_id", "task_0")
            code = arguments.get("code", "")
            exec_res = await self.bridge.execute_task(task_id, code)
            return {
                "status": "SUCCESS" if exec_res.get("status") == "SUCCESS" else "FAILED",
                "stdout": exec_res.get("stdout", ""),
                "stderr": exec_res.get("stderr", ""),
                "metrics": exec_res.get("metrics", {}),
                "execution_time": exec_res.get("execution_time", 0.0)
            }
        elif tool_name == "get_trajectory_status":
            plan_id = arguments.get("plan_id", "DEFAULT_PLAN")
            director = self.get_or_create_director(plan_id)
            deadlock_res = director.detect_deadlock()
            if isinstance(deadlock_res, dict):
                is_deadlocked = deadlock_res.get("is_deadlocked", False)
                cycle_info = deadlock_res.get("cycle_info", deadlock_res.get("cycles", []))
            elif isinstance(deadlock_res, (list, tuple)):
                is_deadlocked = deadlock_res[0] if isinstance(deadlock_res[0], bool) else False
                cycle_info = deadlock_res[1] if len(deadlock_res) > 1 else []
            else:
                is_deadlocked = bool(deadlock_res)
                cycle_info = []
            return {
                "plan_id": plan_id,
                "nodes": list(director.nodes.keys()),
                "executable_nodes": [n.node_id for n in director.get_executable_nodes()],
                "is_deadlocked": bool(is_deadlocked),
                "cycle_info": cycle_info
            }
        else:
            return {"status": "ERROR", "message": f"Unknown tool: {tool_name}"}
