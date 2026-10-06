"""Sovereign Failover Event Recorder and Vault Alerter."""

import time
import os
import sys

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.cloud_offload import CloudOffloadEngine

class FailoverLogger:
    def __init__(self):
        self.offloader = CloudOffloadEngine()

    def record_failover(self, from_model: str, to_model: str, reason: str, root_index: int) -> dict:
        event = {
            "timestamp": time.time(),
            "root_index": root_index,
            "primary_model": from_model,
            "escalated_model": to_model,
            "reason": reason
        }
        target_path = f"telemetry/alerts/failover_{int(event['timestamp'])}.json"
        self.offloader.put_state(target_path, event)
        return event
