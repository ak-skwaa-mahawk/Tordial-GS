"""Gemini / 8-Cloud Grid Bridge for Sovereign Mesh Reasoning.

Interfaces directly with the Google AI Studio Generative Language API 
(Project: gen-lang-client-0886380232) on the Free Tier with exponential backoff.
"""

import os
import time
import json
import urllib.request
import urllib.error

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiBridge:
    def __init__(self, api_key: str = None, model: str = "gemini-3.8-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = model

    def query(
        self,
        prompt: str,
        system_prompt: str = "You are an autonomous scientific reasoning agent.",
        retries: int = 3,
        backoff_sec: float = 2.0
    ) -> dict:
        if not self.api_key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not set. Export it or pass api_key to GeminiBridge."
            }

        url = f"{GEMINI_API_BASE}/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        req_data = json.dumps(payload).encode("utf-8")

        for attempt in range(1, retries + 1):
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return {"success": False, "error": "No candidates returned", "raw": data}

                    content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

                    return {
                        "success": True,
                        "content": content.strip(),
                        "tokens_used": tokens,
                        "model": self.model
                    }
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                # Handle temporary capacity spikes (503) or rate limits (429)
                if e.code in (429, 503) and attempt < retries:
                    wait_time = backoff_sec * (2 ** (attempt - 1))
                    time.sleep(wait_time)
                    continue
                return {"success": False, "error": f"HTTP {e.code}: {err_body}"}
            except Exception as e:
                return {"success": False, "error": str(e)}


if __name__ == "__main__":
    bridge = GeminiBridge()
    res = bridge.query("Validate E8 root index #12 geodesic routing stability under Lyapunov exponent -6.992.")
    print(json.dumps(res, indent=2))
