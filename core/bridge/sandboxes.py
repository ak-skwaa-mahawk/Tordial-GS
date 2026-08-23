"""Subprocess Sandbox Runner:
Executes arbitrary Python code in an isolated subprocess with strict timeouts,
output buffer limits, and structured metric parsing.
"""
import asyncio
import json
import os
import sys
import tempfile
from typing import Dict, Any, Optional


class SubprocessSandbox:
    def __init__(self, timeout_seconds: float = 10.0, max_output_chars: int = 4096):
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    async def execute_code(
        self,
        code_string: str,
        env_vars: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes a Python code string in an isolated subprocess and captures standard streams and metrics."""
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Ensure project root is available to subprocess if needed
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env["PYTHONPATH"] = f"{repo_root}:{env.get('PYTHONPATH', '')}"

        # Write execution code to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
            tmp_file.write(code_string)
            tmp_script_path = tmp_file.name

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                tmp_script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir or os.getcwd(),
                env=env
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                return {
                    "status": "TIMEOUT",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Execution timed out after {self.timeout_seconds} seconds.",
                    "metrics": {},
                    "summary": f"Process killed: timeout exceeded ({self.timeout_seconds}s)"
                }

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")[:self.max_output_chars]
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")[:self.max_output_chars]
            exit_code = proc.returncode

            # Extract metrics if output includes standard delimiter
            metrics = {}
            summary = stdout_str.strip().splitlines()[-1] if stdout_str.strip() else ""

            for line in stdout_str.splitlines():
                if line.startswith("__METRICS__="):
                    try:
                        metrics = json.loads(line.replace("__METRICS__=", "").strip())
                    except Exception:
                        pass

            is_success = exit_code == 0
            return {
                "status": "SUCCESS" if is_success else "FAILED",
                "exit_code": exit_code,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "metrics": metrics,
                "summary": summary if is_success else (stderr_str.strip().splitlines()[-1] if stderr_str.strip() else f"Process failed with exit code {exit_code}")
            }

        finally:
            if os.path.exists(tmp_script_path):
                try:
                    os.remove(tmp_script_path)
                except OSError:
                    pass
