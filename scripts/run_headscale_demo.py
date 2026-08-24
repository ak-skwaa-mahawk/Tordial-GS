import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import asyncio
from simulations.virtual_headscale_cluster import VirtualHeadscaleMesh

async def main():
    mesh = VirtualHeadscaleMesh(node_names=["ALPHA", "BETA", "GAMMA"])
    
    print("--- 1. NORMAL MESH TRAFFIC ---")
    s1 = await mesh.run_traffic_storm(burst_count=6)
    print(f"Handoffs: {s1['successful_handoffs']} | Settled TXs: {s1['total_settled_transactions']}")
    
    print("\n--- 2. DROPPING NODE BETA ---")
    mesh.drop_node("BETA")
    s2 = await mesh.run_traffic_storm(burst_count=6)
    print(f"Active Nodes: {s2['active_nodes']} | Handoffs: {s2['successful_handoffs']}")
    
    print("\n--- 3. DEGRADING ALPHA -> GAMMA LINK ---")
    mesh.degrade_link("ALPHA", "GAMMA")
    s3 = await mesh.run_traffic_storm(burst_count=6)
    print(f"Handoffs under degraded link: {s3['successful_handoffs']}")
    
    print("\n--- 4. RECOVERING NODE BETA & HEALING LINK ---")
    mesh.recover_node("BETA")
    mesh.heal_link("ALPHA", "GAMMA")
    s4 = await mesh.run_traffic_storm(burst_count=6)
    print(f"Active Nodes: {s4['active_nodes']} | Total Hops: {s4['total_hops_traversed']}")

if __name__ == "__main__":
    asyncio.run(main())
