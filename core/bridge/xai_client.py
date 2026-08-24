import json
import io
import sys
import logging
import numpy as np
from typing import Dict, Any, List
from core.mesh.router import SovereignMeshRouter

logger = logging.getLogger("xai_client")

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "scientific_director_plan",
            "description": "Submits a scientific research plan node",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "node_id": {"type": "string"},
                    "hypothesis": {"type": "string"},
                    "parameters": {"type": "object"}
                },
                "required": ["plan_id", "node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sandbox_execute",
            "description": "Executes simulation python script in sandbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "code": {"type": "string"}
                },
                "required": ["task_id", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trajectory_status",
            "description": "Fetches active simulation trajectory telemetry and state",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "trajectory_id": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "e8_mesh_burst_dispatch",
            "description": "Routes burst packets through the 240 E8 root highways",
            "parameters": {
                "type": "object",
                "properties": {
                    "queue_size": {"type": "number"},
                    "grad_temp": {"type": "number"},
                    "qber": {"type": "number"},
                    "channel_loss": {"type": "number"},
                    "effective_strain": {"type": "number"},
                    "coherence": {"type": "number"},
                    "entropy": {"type": "number"},
                    "phase_drift": {"type": "number"},
                    "budget_sats": {"type": "integer"}
                }
            }
        }
    }
]

class XAIBridgeEngine:
    def __init__(self, node_id: str = "Tordial-GS-Bridge"):
        self.node_id = node_id
        self.router = SovereignMeshRouter(node_id=self.node_id)
        self.registered_nodes = {}

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches incoming tool calls to local engine handlers."""
        if tool_name == "scientific_director_plan":
            plan_id = arguments.get("plan_id")
            node_id = arguments.get("node_id")
            self.registered_nodes[node_id] = arguments
            return {
                "status": "NODE_REGISTERED",
                "plan_id": plan_id,
                "node_id": node_id,
                "executable_now": True
            }

        elif tool_name == "get_trajectory_status":
            trajectory_id = arguments.get("trajectory_id", "DEFAULT")
            plan_id = arguments.get("plan_id", "DEFAULT")
            return {
                "status": "ACTIVE",
                "plan_id": plan_id,
                "trajectory_id": trajectory_id,
                "nodes": self.registered_nodes,
                "node_count": len(self.registered_nodes),
                "is_deadlocked": False,
                "timestamp": 1787498400.0
            }

        elif tool_name == "sandbox_execute":
            code = arguments.get("code", "")
            local_vars = {}
            exec_globals = {"json": json, "np": np}
            
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            
            try:
                exec(code, exec_globals, local_vars)
                stdout_str = redirected_output.getvalue()
                
                metrics = {}
                for line in stdout_str.splitlines():
                    if "__METRICS__=" in line:
                        payload = line.split("__METRICS__=", 1)[1].strip()
                        metrics = json.loads(payload)
                        break
                        
                if not metrics and "telemetry" in local_vars:
                    metrics = local_vars["telemetry"]
                    
                return {"status": "SUCCESS", "metrics": metrics, "stdout": stdout_str}
            except Exception as e:
                return {"status": "EXEC_ERROR", "error": str(e)}
            finally:
                sys.stdout = old_stdout

        elif tool_name == "e8_mesh_burst_dispatch":
            queue_size = float(arguments.get("queue_size", 4.0))
            grad_temp = float(arguments.get("grad_temp", 3.0))
            qber = float(arguments.get("qber", 0.01))
            channel_loss = float(arguments.get("channel_loss", 0.02))
            effective_strain = float(arguments.get("effective_strain", 3.5))
            coherence = float(arguments.get("coherence", 0.98))
            entropy = float(arguments.get("entropy", 0.2))
            phase_drift = float(arguments.get("phase_drift", 0.002))
            budget_sats = int(arguments.get("budget_sats", 500))

            telemetry_8d = self.router.build_telemetry_vector(
                queue_size=queue_size,
                grad_temp=grad_temp,
                qber=qber,
                channel_loss=channel_loss,
                effective_strain=effective_strain,
                coherence=coherence,
                entropy=entropy,
                phase_drift=phase_drift
            )

            record = self.router.route_burst(telemetry_8d, budget_sats=budget_sats)
            return {
                "status": "DISPATCH_EXECUTED",
                "record": record
            }

        else:
            return {"status": "UNKNOWN_TOOL", "tool_name": tool_name}
