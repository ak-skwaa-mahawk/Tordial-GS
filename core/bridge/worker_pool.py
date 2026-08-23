"""Master-Worker Delegation Bridge: Async dispatch and context compression."""
import asyncio
from typing import Dict, Any, Callable

class WorkerBridge:
    def __init__(self, max_concurrency: int = 4):
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_task(self, task_id: str, runner_func: Callable, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self.semaphore:
            try:
                raw_result = await runner_func(payload)
                return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "compressed_context": raw_result.get("summary", ""),
                    "metrics": raw_result.get("metrics", {})
                }
            except Exception as exc:
                return {
                    "task_id": task_id,
                    "status": "FAILED",
                    "error": str(exc),
                    "compressed_context": f"Error during execution: {str(exc)[:120]}"
                }
