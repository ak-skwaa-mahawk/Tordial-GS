"""Rolling Time-Series Dispersion and Attractor Drift Recorder.

Maintains rolling temporal history of mesh transport dispersion and Lyapunov
convergence metrics to expose long-term degradation patterns, hydrating
existing snapshots from the sovereign vault upon startup.
"""

import time
import json
import os
import sys
import subprocess

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.cloud_offload import CloudOffloadEngine

MAX_LOCAL_WINDOW = 120  # Keep 120 intervals (2 hours at 60s intervals)

class TelemetryTimeSeries:
    def __init__(self, hydrate: bool = True):
        self.offloader = CloudOffloadEngine()
        self.history: list[dict] = []
        if hydrate:
            self._hydrate_from_vault()

    def _hydrate_from_vault(self):
        try:
            target = "gdrive:tordial_mesh_vault/telemetry/metrics/dispersion_timeseries.json"
            res = subprocess.run(
                ["rclone", "cat", target, "--log-level", "ERROR"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                samples = data.get("samples", [])
                if isinstance(samples, list):
                    self.history = samples[-MAX_LOCAL_WINDOW:]
        except Exception:
            pass

    def append_sample(self, digest: dict) -> dict:
        entry = {
            "timestamp": digest.get("timestamp", time.time()),
            "mean_delay_ms": digest.get("jitter_stats", {}).get("mean_delay_ms", 0.0),
            "jitter_ms": digest.get("jitter_stats", {}).get("jitter_ms", 0.0),
            "min_delay_ms": digest.get("jitter_stats", {}).get("min_delay_ms", 0.0),
            "max_delay_ms": digest.get("jitter_stats", {}).get("max_delay_ms", 0.0),
            "all_healthy": digest.get("all_healthy", False),
            "monitored_roots": digest.get("monitored_roots_count", 0)
        }
        self.history.append(entry)
        if len(self.history) > MAX_LOCAL_WINDOW:
            self.history.pop(0)

        # Offload current rolling series snapshot to cloud vault
        payload = {
            "last_updated": time.time(),
            "window_size": len(self.history),
            "samples": self.history
        }
        self.offloader.put_state("telemetry/metrics/dispersion_timeseries.json", payload)
        return payload
