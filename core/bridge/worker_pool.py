"""Master-Worker Delegation Bridge: Async dispatch, concurrency gating, and context compression."""
import asyncio
import re
from typing import Dict, Any, Callable

class WorkerBridge:
    def __init__(self, max_concurrency: int = 4):
        self.semaphore = asyncio.Semaphore(max_concurrency)

    @staticmethod
    def compress_traceback(raw_trace: str) -> str:
        """Extracts the critical error boundary without polluting the Master model's context window."""
        if not raw_trace:
            return ""
        lines = [line.strip() for line in raw_trace.splitlines() if line.strip()]
        # Capture the final exception line and the immediate originating call
        important = [l for l in lines if l.startswith("File ") or "Error" in l or "Exception" in l]
        if important:
            return " | ".join(important[-2:])
        return lines[-1] if lines else "Unknown Error"

    async def execute_task(self, task_id: str, runner_func: Callable, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self.semaphore:
            try:
                raw_result = await runner_func(payload)
                return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "compressed_context": raw_result.get("summary", "Execution completed successfully."),
                    "metrics": raw_result.get("metrics", {}),
                    "token_footprint": len(str(raw_result))
                }
            except Exception as exc:
                compressed_err = self.compress_traceback(str(exc))
                return {
                    "task_id": task_id,
                    "status": "FAILED",
                    "error": str(exc),
                    "compressed_context": f"Execution halted: {compressed_err}",
                    "token_footprint": len(str(exc))
                }
