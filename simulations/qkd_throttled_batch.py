import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import time
from core.director.thermal_governor import ThermalGovernor

async def dummy_quantum_task(task_id: int):
    # Simulate CPU burst
    _ = [x**2 for x in range(1000000)]
    return f"Task-{task_id} OK"

async def run_governed_batch():
    governor = ThermalGovernor(warn_temp=48.0, throttle_temp=54.0, pause_temp=60.0)
    tasks = list(range(12))
    
    print(f"[*] Starting 12-task batch under Thermal Governor...")
    print(f"[*] Initial SoC Temperature: {governor.get_max_temperature():.1f}°C\n")
    
    idx = 0
    while idx < len(tasks):
        safe_workers = await governor.guard_concurrency(current_concurrency=4)
        batch = tasks[idx : idx + safe_workers]
        
        print(f"[{time.strftime('%H:%M:%S')}] Dispatching {len(batch)} tasks with safe workers={safe_workers} (SoC Temp: {governor.get_max_temperature():.1f}°C)")
        await asyncio.gather(*(dummy_quantum_task(t) for t in batch))
        
        idx += safe_workers

    print(f"\n[+] Batch complete. Final SoC Temperature: {governor.get_max_temperature():.1f}°C")

if __name__ == "__main__":
    asyncio.run(run_governed_batch())
