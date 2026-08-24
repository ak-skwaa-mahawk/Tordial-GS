import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Set
from core.mesh.router import SovereignMeshRouter
from core.mesh.ledger_settlement import SovereignLedgerEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("headscale_sim")

class VirtualHeadscaleMesh:
    def __init__(self, node_names: List[str] = None, ledger_engine: SovereignLedgerEngine = None):
        self.node_names = node_names or ["HEADSCALE-ALPHA", "HEADSCALE-BETA", "HEADSCALE-GAMMA"]
        self.nodes: Dict[str, SovereignMeshRouter] = {
            name: SovereignMeshRouter(node_id=name) for name in self.node_names
        }
        self.dropped_nodes: Set[str] = set()
        self.degraded_links: Set[tuple] = set()
        self.peer_links = self._establish_mesh_topology()
        self.ledger = ledger_engine or SovereignLedgerEngine()
        self.global_handoff_log: List[Dict[str, Any]] = []

    def _establish_mesh_topology(self) -> Dict[str, List[str]]:
        links = {}
        for node in self.node_names:
            links[node] = [peer for peer in self.node_names if peer != node and peer not in self.dropped_nodes]
        return links

    def drop_node(self, node_id: str):
        """Simulates complete node disconnection from the Headscale mesh."""
        self.dropped_nodes.add(node_id)
        self.peer_links = self._establish_mesh_topology()
        logger.warning(f"❌ [TOPOLOGY UPDATE]: Node {node_id} dropped from mesh")

    def recover_node(self, node_id: str):
        """Restores a dropped node back to active routing."""
        self.dropped_nodes.discard(node_id)
        self.peer_links = self._establish_mesh_topology()
        logger.info(f"🔄 [TOPOLOGY UPDATE]: Node {node_id} recovered and active")

    def degrade_link(self, from_node: str, to_node: str):
        """Simulates high channel loss/QBER on a specific directional link."""
        self.degraded_links.add((from_node, to_node))
        logger.warning(f"⚠️ [LINK DEGRADED]: High packet loss injected on {from_node} -> {to_node}")

    def heal_link(self, from_node: str, to_node: str):
        """Restores standard link fidelity."""
        self.degraded_links.discard((from_node, to_node))
        logger.info(f"✨ [LINK RESTORED]: Fidelity restored on {from_node} -> {to_node}")

    async def forward_burst_packet(
        self,
        origin_node: str,
        telemetry_8d: np.ndarray,
        budget_sats: int = 500,
        ttl: int = 3
    ) -> Dict[str, Any]:
        """Routes burst packets dynamically with link degradation and drop awareness."""
        if origin_node in self.dropped_nodes:
            return {
                "origin": origin_node,
                "total_hops": 0,
                "final_status": "ORIGIN_NODE_DROPPED",
                "trace": []
            }

        current_node = origin_node
        hop_trace = []

        for hop in range(ttl):
            if current_node in self.dropped_nodes:
                hop_trace.append({
                    "hop": hop + 1,
                    "node_id": current_node,
                    "status": "NODE_UNREACHABLE_DROPPED"
                })
                break

            router = self.nodes[current_node]
            record = router.route_burst(telemetry_8d, budget_sats=budget_sats)
            decision = record["decision"]
            status = decision["status"]

            hop_info = {
                "hop": hop + 1,
                "node_id": current_node,
                "status": status,
                "root_index": decision.get("selected_root_index"),
                "weight": decision.get("dispatch_weight", 0.0)
            }
            hop_trace.append(hop_info)

            if status != "E8_HIGHWAY_DISPATCHED":
                break

            active_peers = self.peer_links.get(current_node, [])
            if not active_peers:
                hop_trace.append({
                    "hop": hop + 2,
                    "node_id": "NONE",
                    "status": "NO_ROUTABLE_PEERS"
                })
                break

            next_node = active_peers[decision["selected_root_index"] % len(active_peers)]
            
            # Apply link physics & degradation penalties
            link_noise = np.random.normal(0, 0.01, size=8)
            link_noise[7] = np.random.normal(0, 0.001)
            
            if (current_node, next_node) in self.degraded_links:
                # Degraded link: High loss, severe QBER, high strain
                telemetry_8d[2] += 0.15  # QBER spike
                telemetry_8d[3] += 0.25  # Channel Loss spike
                telemetry_8d[4] += 1.5   # Strain spike
                telemetry_8d = (telemetry_8d * 0.90) + link_noise
            else:
                telemetry_8d = (telemetry_8d * 0.98) + link_noise
                
            telemetry_8d[7] = np.clip(telemetry_8d[7], -0.005, 0.005)
            current_node = next_node

        handoff_entry = {
            "origin": origin_node,
            "total_hops": len(hop_trace),
            "final_status": hop_trace[-1]["status"],
            "trace": hop_trace
        }
        
        settlement_result = self.ledger.settle_burst_dispatch(handoff_entry, budget_sats=budget_sats)
        handoff_entry["settlement"] = settlement_result
        
        self.global_handoff_log.append(handoff_entry)
        return handoff_entry

    async def run_traffic_storm(self, burst_count: int = 30) -> Dict[str, Any]:
        logger.info(f"🌐 Initiating Headscale traffic storm with {burst_count} bursts...")
        tasks = []
        active_nodes = [n for n in self.node_names if n not in self.dropped_nodes]
        if not active_nodes:
            return {"status": "ALL_NODES_DROPPED"}

        for i in range(burst_count):
            origin = active_nodes[i % len(active_nodes)]
            telemetry = np.array([4.2, 3.1, 0.01, 0.02, 3.6, 0.98, 0.15, 0.002]) + np.random.normal(0, 0.02, 8)
            telemetry[7] = np.clip(telemetry[7], -0.005, 0.005)
            tasks.append(self.forward_burst_packet(origin_node=origin, telemetry_8d=telemetry, budget_sats=500))

        results = await asyncio.gather(*tasks)
        dispatched_hops = sum(r["total_hops"] for r in results if r["final_status"] == "E8_HIGHWAY_DISPATCHED")
        settled_count = sum(1 for r in results if r.get("settlement", {}).get("status") == "SETTLED")

        return {
            "nodes_in_mesh": len(self.node_names),
            "active_nodes": len(active_nodes),
            "bursts_injected": burst_count,
            "successful_handoffs": sum(1 for r in results if r["final_status"] == "E8_HIGHWAY_DISPATCHED"),
            "total_settled_transactions": settled_count,
            "total_hops_traversed": dispatched_hops,
            "per_node_queue_depths": {
                name: float(np.max(router.queue_depths)) for name, router in self.nodes.items()
            }
        }
