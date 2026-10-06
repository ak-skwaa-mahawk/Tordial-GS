"""E8 Geodesic Router with Live Gemini Dynamic Attractor Verification.

Evaluates metric drift against Lyapunov limits and offloads verification
decisions directly to Google Drive vault telemetry.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.gemini_bridge import GeminiBridge
from core.mesh.cloud_offload import CloudOffloadEngine

class E8GeodesicRouter:
    def __init__(self):
        self.bridge = GeminiBridge()
        self.offloader = CloudOffloadEngine()

    def evaluate_vector(self, root_index: int, phase_drift: float, lyapunov: float) -> dict:
        prompt = (
            f"Analyze routing vector for E8 root index #{root_index}. "
            f"Observed Phase Drift: {phase_drift} rad, Lyapunov Exponent: {lyapunov}. "
            f"Determine if transverse contraction maintains sovereign mesh stability. "
            f"Return status formatted as ROUTE_STABLE or ROUTE_DEVIANT with vector delta."
        )

        res = self.bridge.query(
            prompt=prompt,
            system_prompt="You are the E8 Topological Mesh Router. Evaluate metric contraction with precision."
        )

        decision = {
            "timestamp": time.time(),
            "root_index": root_index,
            "metrics": {
                "phase_drift": phase_drift,
                "lyapunov": lyapunov
            },
            "routing_engine": res.get("model"),
            "success": res.get("success"),
            "verdict": res.get("content", "").strip() if res.get("success") else res.get("error")
        }

        # Pipe routing journal directly to Google Drive
        target_path = f"telemetry/routing/root_{root_index}_eval.json"
        offload_result = self.offloader.put_state(target_path, decision)
        decision["cloud_offload"] = offload_result

        return decision

if __name__ == "__main__":
    router = E8GeodesicRouter()
    print("[*] Evaluating E8 root index #12...")
    out = router.evaluate_vector(root_index=12, phase_drift=0.00000, lyapunov=-6.992)
    print("\nRouting Evaluation:\n", json.dumps(out, indent=2))
