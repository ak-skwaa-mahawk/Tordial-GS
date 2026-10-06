"""Sovereign Failover Event Recorder and Vault Alerter with Cooldown Gating."""

import time
import os
import sys

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.cloud_offload import CloudOffloadEngine

COOLDOWN_WINDOW_SEC = 30.0

class FailoverLogger:
    def __init__(self):
        self.offloader = CloudOffloadEngine()
        self._last_events: dict[int, tuple[float, str]] = {}

    def record_failover(self, from_model: str, to_model: str, reason: str, root_index: int) -> dict:
        now = time.time()
        
        # Check cooldown to avoid flooding vault during cascade storms
        if root_index in self._last_events:
            last_ts, last_reason = self._last_events[root_index]
            if (now - last_ts < COOLDOWN_WINDOW_SEC) and (last_reason == reason):
                return {
                    "timestamp": now,
                    "root_index": root_index,
                    "primary_model": from_model,
                    "escalated_model": to_model,
                    "reason": reason,
                    "suppressed": True
                }

        self._last_events[root_index] = (now, reason)
        event = {
            "timestamp": now,
            "root_index": root_index,
            "primary_model": from_model,
            "escalated_model": to_model,
            "reason": reason,
            "suppressed": False
        }
        target_path = f"telemetry/alerts/failover_{int(now)}.json"
        self.offloader.put_state(target_path, event)
        return event
