"""Master-Worker Delegation Bridge: Async dispatch, concurrency gating,
Subprocess sandbox execution, and context compression.
"""
import asyncio
from typing import Dict, Any, Callable, Optional, Union

from core.bridge.sandboxes import SubprocessSandbox


class WorkerBridge:
    def __init__(self, max_concurrency: int = 4, sandbox_timeout: float = 10.0):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.sandbox = SubprocessSandbox(timeout_seconds=sandbox_timeout)

    @staticmethod
    def compress_traceback(raw_trace: str) -> str:
        """Extracts the critical error boundary without polluting the Master model's context window."""
        if not raw_trace:
            return ""
        lines = [line.strip() for line in raw_trace.splitlines() if line.strip()]
        important = [l for l in lines if l.startswith("File ") or "Error" in l or "Exception" in l]
        if important:
            return " | ".join(important[-2:])
        return lines[-1] if lines else "Unknown Error"

    async def execute_task(
        self,
        task_id: str,
        runner_or_code: Union[Callable, str],
        payload: Optional[Dict[str, Any]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executes a task either by evaluating an async runner function or running code in the isolated subprocess sandbox."""
        payload = payload or {}
        async with self.semaphore:
            # 1. Code-string sandbox execution path
            if isinstance(runner_or_code, str):
                sandbox_res = await self.sandbox.execute_code(runner_or_code, env_vars=env_vars)
                status = sandbox_res["status"]
                is_success = status == "SUCCESS"
                err_text = sandbox_res.get("stderr", "")
                compressed_err = self.compress_traceback(err_text) if not is_success else ""

                return {
                    "task_id": task_id,
                    "status": status,
                    "exit_code": sandbox_res.get("exit_code", 0),
                    "summary": sandbox_res.get("summary", ""),
                    "compressed_context": sandbox_res.get("summary", "") if is_success else f"Execution halted: {compressed_err}",
                    "metrics": sandbox_res.get("metrics", {}),
                    "stdout": sandbox_res.get("stdout", ""),
                    "stderr": sandbox_res.get("stderr", ""),
                    "token_footprint": len(sandbox_res.get("stdout", "")) + len(sandbox_res.get("stderr", ""))
                }

            # 2. Async callable runner path
            try:
                raw_result = await runner_or_code(payload)
                return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "exit_code": 0,
                    "summary": raw_result.get("summary", "Execution completed successfully."),
                    "compressed_context": raw_result.get("summary", "Execution completed successfully."),
                    "metrics": raw_result.get("metrics", {}),
                    "token_footprint": len(str(raw_result))
                }
            except Exception as exc:
                compressed_err = self.compress_traceback(str(exc))
                return {
                    "task_id": task_id,
                    "status": "FAILED",
                    "exit_code": -1,
                    "error": str(exc),
                    "compressed_context": f"Execution halted: {compressed_err}",
                    "metrics": {},
                    "token_footprint": len(str(exc))
                }
