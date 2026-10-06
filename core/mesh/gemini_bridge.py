"""Gemini / Sovereign Mesh Bridge with Full Multi-Part Reassembly and Lite Fallback.

Targeting gen-lang-client-0886380232 with automatic failover across verified models.
"""

import os
import time
import random
import json
import urllib.request
import urllib.error
import socket

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL_CASCADE = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
]


class GeminiBridge:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.primary_model = model or "gemini-3.6-flash"

    def query(
        self,
        prompt: str,
        system_prompt: str = "You are an autonomous scientific reasoning agent.",
        retries: int = 3,
        backoff_sec: float = 3.0,
    ) -> dict:
        if not self.api_key:
            return {"success": False, "error": "GEMINI_API_KEY is not set."}

        candidates = [self.primary_model] + [
            m for m in MODEL_CASCADE if m != self.primary_model
        ]

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        last_error = ""

        for current_model in candidates:
            url = f"{GEMINI_API_BASE}/{current_model}:generateContent?key={self.api_key}"

            for attempt in range(1, retries + 1):
                req = urllib.request.Request(
                    url,
                    data=body_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                try:
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        cand_list = data.get("candidates", [])
                        if not cand_list:
                            return {
                                "success": False,
                                "error": "No candidates returned",
                                "raw": data,
                            }

                        parts = cand_list[0].get("content", {}).get("parts", [])
                        full_text = "".join(p.get("text", "") for p in parts)
                        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

                        return {
                            "success": True,
                            "content": full_text.strip(),
                            "tokens_used": tokens,
                            "model": current_model,
                        }

                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="ignore")
                    last_error = f"HTTP {e.code} on {current_model}: {err_body}"

                    if e.code in (429, 503):
                        sleep_time = (backoff_sec * (2 ** (attempt - 1))) + random.uniform(1.0, 2.5)
                        print(
                            f"[!] {current_model} saturated (HTTP {e.code}). Retrying in {sleep_time:.1f}s (attempt {attempt}/{retries})..."
                        )
                        time.sleep(sleep_time)
                        continue
                    elif e.code == 404:
                        break
                    else:
                        return {"success": False, "error": last_error}

                except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
                    last_error = f"Timeout on {current_model}: {str(e)}"
                    sleep_time = (backoff_sec * (2 ** (attempt - 1))) + random.uniform(1.0, 2.5)
                    print(
                        f"[!] {current_model} timed out. Retrying in {sleep_time:.1f}s (attempt {attempt}/{retries})..."
                    )
                    time.sleep(sleep_time)
                    continue

                except Exception as e:
                    return {"success": False, "error": str(e)}

            print(f"[-] Model {current_model} failed after {retries} attempts. Cascading to next candidate...")

        return {"success": False, "error": f"Cascade exhausted: {last_error}"}


if __name__ == "__main__":
    bridge = GeminiBridge()
    res = bridge.query(
        "Validate E8 root index #12 geodesic routing stability under Lyapunov exponent -6.992."
    )
    print(json.dumps(res, indent=2))
