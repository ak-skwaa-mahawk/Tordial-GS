"""Kimi / Moonshot AI Bridge for Sovereign Mesh Reasoning.

Interfaces with the Moonshot API (api.moonshot.ai/v1) using an OpenAI-compatible
schema for dual-routed scientific reasoning and DAG dispatch validation.
"""

import os
import json
import urllib.request
import urllib.error

DEFAULT_BASE_URL = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1/chat/completions")


class KimiBridge:
    def __init__(self, api_key: str = None, model: str = "kimi-k3", base_url: str = None, timeout: int = None):
        self.api_key = api_key or os.environ.get("MOONSHOT_API_KEY", "").strip()
        self.model = model
        self.base_url = base_url or DEFAULT_BASE_URL
        # Set dynamic timeout based on model reasoning latency
        if timeout:
            self.timeout = timeout
        elif "code" in self.model:
            self.timeout = 180
        else:
            self.timeout = 60

    def query(
        self,
        prompt: str,
        system_prompt: str = "You are an autonomous scientific reasoning agent.",
        think_effort: str = "low",
    ) -> dict:
        if not self.api_key:
            raise ValueError("MOONSHOT_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 1.0,
        }

        if "k3" in self.model:
            payload["reasoning_effort"] = think_effort

        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]["message"]
                return {
                    "success": True,
                    "content": choice.get("content", ""),
                    "reasoning_content": choice.get("reasoning_content", ""),
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                    "model": data.get("model", self.model),
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {"success": False, "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    bridge = KimiBridge()
    res = bridge.query("Validate octahedral tilt angle for cubic perovskite SrTiO3. Keep response brief.")
    print(json.dumps(res, indent=2))
