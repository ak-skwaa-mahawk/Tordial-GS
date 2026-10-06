"""E8 Geodesic Router with Polytope Coordinates and Gemini Attractor Verification.

Evaluates metric drift against Lyapunov limits using exact canonical 8D coordinates
and offloads verification decisions directly to Google Drive vault telemetry.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.gemini_bridge import GeminiBridge
from core.mesh.cloud_offload import CloudOffloadEngine
from core.mesh.e8_polytope import get_root_vector

class E8GeodesicRouter:
    def __init__(self):
        self.bridge = GeminiBridge()
        self.offloader = CloudOffloadEngine()

    def evaluate_vector(self, root_index: int, phase_drift: float, lyapunov: float) -> dict:
        root_coords = get_root_vector(root_index)
        prompt = (
            f"Analyze routing vector for canonical E8 root index #{root_index}.\n"
            f"Coordinates: {list(root_coords)}\n"
            f"Observed Phase Drift: {phase_drift} rad\n"
            f"Lyapunov Exponent: {lyapunov}\n\n"
            f"Instructions:\n"
            f"1. Sentence 1 MUST start with either 'STATUS: ROUTE_STABLE' or 'STATUS: ROUTE_DEVIANT'.\n"
            f"2. Provide an 8-dimensional corrective delta vector [Δθ₁..Δθ₈] if deviant.\n"
            f"3. Keep proof concise."
        )

        res = self.bridge.query(
            prompt=prompt,
            system_prompt="You are the E8 Topological Mesh Router. Output strict status headers."
        )

        decision = {
            "timestamp": time.time(),
            "root_index": root_index,
            "root_coords": root_coords,
            "metrics": {
                "phase_drift": phase_drift,
                "lyapunov": lyapunov
            },
            "routing_engine": res.get("model"),
            "success": res.get("success"),
            "verdict": res.get("content", "").strip() if res.get("success") else res.get("error")
        }

        target_path = f"telemetry/routing/root_{root_index}_eval.json"
        offload_result = self.offloader.put_state(target_path, decision)
        decision["cloud_offload"] = offload_result

        return decision

if __name__ == "__main__":
    router = E8GeodesicRouter()
    print("[*] Evaluating E8 root index #12 with coordinate mapping...")
    out = router.evaluate_vector(root_index=12, phase_drift=0.00000, lyapunov=-6.992)
    print("\nRouting Evaluation:\n", json.dumps(out, indent=2))
