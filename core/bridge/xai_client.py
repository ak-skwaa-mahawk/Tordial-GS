"""xAI / Grok Native Function Calling Tool Bridge:
Maps ScientificDirector DAG graph operations, SubprocessSandbox execution,
and LongHorizonEvaluator metrics into OpenAI/xAI-compatible tool schemas.
"""
import os
import json
from typing import Dict, Any, List, Optional
from core.director.scientific_director import ScientificDirector
from core.bridge.worker_pool import WorkerBridge


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "scientific_director_plan",
            "description": "Initialize or append hypothesis nodes to a directed acyclic experiment plan graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "Unique identifier for the research experiment plan."
                    },
                    "node_id": {
                        "type": "string",
                        "description": "Identifier for the hypothesis step (e.g. 'H1_calibrate_phase')."
                    },
                    "hypothesis": {
                        "type": "string",
                        "description": "Scientific hypothesis or objective of this execution step."
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Input parameters or target invariant bounds for the node.",
                        "additionalProperties": True
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of prerequisite node_ids that must be VERIFIED prior to execution."
                    }
                },
                "required": ["plan_id", "node_id", "hypothesis"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sandbox_execute",
            "description": "Execute raw Python scientific computation code inside an isolated subprocess sandbox with timeout and metric extraction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Tracking identifier for the execution."
                    },
                    "code": {
                        "type": "string",
                        "description": "Complete executable Python code string."
                    },
                    "timeout_seconds": {
                        "type": "number",
                        "description": "Optional maximum execution time (defaults to 10.0s)."
                    }
                },
                "required": ["task_id", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trajectory_status",
            "description": "Retrieve current hypothesis graph statuses, deadlock states, and trajectory efficiency metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan identifier to inspect."
                    }
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
        """Dispatches an incoming LLM tool call to the respective local engine component."""
        if tool_name == "scientific_director_plan":
            plan_id = arguments.get("plan_id", "DEFAULT_PLAN")
            director = self.get_or_create_director(plan_id)
            node = director.add_step(
                node_id=arguments["node_id"],
                hypothesis=arguments["hypothesis"],
                parameters=arguments.get("parameters", {}),
                dependencies=arguments.get("dependencies", [])
            )
            return {
                "status": "NODE_REGISTERED",
                "plan_id": plan_id,
                "node_id": node.node_id,
                "hypothesis": node.hypothesis,
                "dependencies": node.dependencies,
                "executable_now": node.node_id in [n.node_id for n in director.get_executable_nodes()]
            }

        elif tool_name == "sandbox_execute":
            task_id = arguments["task_id"]
            code = arguments["code"]
            res = await self.bridge.execute_task(task_id=task_id, runner_or_code=code)
            return {
                "task_id": res.get("task_id"),
                "status": res.get("status"),
                "exit_code": res.get("exit_code"),
                "summary": res.get("summary"),
                "compressed_context": res.get("compressed_context"),
                "metrics": res.get("metrics"),
                "token_footprint": res.get("token_footprint")
            }

        elif tool_name == "get_trajectory_status":
            plan_id = arguments["plan_id"]
            if plan_id not in self.directors:
                return {"status": "NOT_FOUND", "message": f"Plan '{plan_id}' does not exist."}
            director = self.directors[plan_id]
            deadlock_info = director.detect_deadlock()
            return {
                "plan_id": plan_id,
                "nodes": {k: v.status for k, v in director.nodes.items()},
                "executable_nodes": [n.node_id for n in director.get_executable_nodes()],
                "is_deadlocked": deadlock_info["is_deadlocked"],
                "reason": deadlock_info.get("reason"),
                "trajectory_efficiency": director.trajectory_efficiency
            }

        return {
            "status": "ERROR",
            "message": f"Unknown tool name: {tool_name}"
        }
