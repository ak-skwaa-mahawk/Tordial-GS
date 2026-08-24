import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import asyncio
import logging
import numpy as np
from typing import Dict, List, Any
from core.mesh.router import SovereignMeshRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("headscale_sim")

class VirtualHeadscaleMesh:
    def __init__(self, node_names: List[str] = None):
        self.node_names = node_names or ["HEADSCALE-ALPHA", "HEADSCALE-BETA", "HEADSCALE-GAMMA"]
        self.nodes: Dict[str, SovereignMeshRouter] = {
            name: SovereignMeshRouter(node_id=name) for name in self.node_names
        }
        self.peer_links = self._establish_mesh_topology()
        self.global_handoff_log: List[Dict[str, Any]] = []

    def _establish_mesh_topology(self) -> Dict[str, List[str]]:
        """Fully connects each virtual Headscale node to every other peer in the mesh."""
        links = {}
        for node in self.node_names:
            links[node] = [peer for peer in self.node_names if peer != node]
        return links

    async def forward_burst_packet(
        self,
        origin_node: str,
        telemetry_8d: np.ndarray,
        budget_sats: int = 500,
        ttl: int = 3
    ) -> Dict[str, Any]:
        """Routes a burst packet hop-by-hop across the virtual mesh using E8 dispatching."""
        current_node = origin_node
        hop_trace = []

        for hop in range(ttl):
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

            # Pick next hop from peer links via modulo projection of the chosen E8 root index
            peers = self.peer_links[current_node]
            next_node = peers[decision["selected_root_index"] % len(peers)]
            
            # Attenuation across physical link: preserve energy above 5.5 and clamp phase drift < 0.01
            link_noise = np.random.normal(0, 0.01, size=8)
            link_noise[7] = np.random.normal(0, 0.001)  # Micro-drift on phase
            telemetry_8d = (telemetry_8d * 0.98) + link_noise
            telemetry_8d[7] = np.clip(telemetry_8d[7], -0.005, 0.005)
            
            current_node = next_node

        handoff_entry = {
            "origin": origin_node,
            "total_hops": len(hop_trace),
            "final_status": hop_trace[-1]["status"],
            "trace": hop_trace
        }
        self.global_handoff_log.append(handoff_entry)
        return handoff_entry

    async def run_traffic_storm(self, burst_count: int = 30) -> Dict[str, Any]:
        """Simulates distributed concurrent burst dispatches across all virtual nodes."""
        logger.info(f"🌐 Initiating Headscale traffic storm with {burst_count} bursts...")
        tasks = []
        
        for i in range(burst_count):
            origin = self.node_names[i % len(self.node_names)]
            telemetry = np.array([4.2, 3.1, 0.01, 0.02, 3.6, 0.98, 0.15, 0.002]) + np.random.normal(0, 0.02, 8)
            telemetry[7] = np.clip(telemetry[7], -0.005, 0.005)
            tasks.append(self.forward_burst_packet(origin_node=origin, telemetry_8d=telemetry, budget_sats=500))

        results = await asyncio.gather(*tasks)
        dispatched_hops = sum(r["total_hops"] for r in results if r["final_status"] == "E8_HIGHWAY_DISPATCHED")
        
        summary = {
            "nodes_in_mesh": len(self.node_names),
            "bursts_injected": burst_count,
            "successful_handoffs": sum(1 for r in results if r["final_status"] == "E8_HIGHWAY_DISPATCHED"),
            "total_hops_traversed": dispatched_hops,
            "per_node_queue_depths": {
                name: float(np.max(router.queue_depths)) for name, router in self.nodes.items()
            }
        }
        return summary
