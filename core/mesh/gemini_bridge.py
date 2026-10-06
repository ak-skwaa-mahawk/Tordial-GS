"""Sovereign Gemini Inference Bridge with Dynamic Failover and Vault Alerting.

Cascades across flash tiers (gemini-3.5-flash-lite -> gemini-3.6-flash -> gemini-3.8-flash)
and logs escalation events to Google Drive upon secondary invocation.
"""

import os
import sys
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.failover_logger import FailoverLogger

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash"
]

class GeminiBridge:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.failover_logger = FailoverLogger()

    def query(self, prompt: str, system_prompt: str = "", root_index: int = 12) -> dict:
        if not self.api_key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY environment variable not configured."
            }

        last_error = None
        for i, model in enumerate(MODELS):
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {
                            "success": True,
                            "content": text,
                            "model": model
                        }
            except Exception as e:
                last_error = str(e)
                # If falling over to a subsequent model in the cascade, log alert
                if i + 1 < len(MODELS):
                    next_model = MODELS[i + 1]
                    try:
                        self.failover_logger.record_failover(
                            from_model=model,
                            to_model=next_model,
                            reason=last_error,
                            root_index=root_index
                        )
                    except Exception as log_err:
                        print(f"[-] Failover logger alert error: {log_err}")

        return {
            "success": False,
            "error": f"All cascade models exhausted. Last error: {last_error}"
        }
