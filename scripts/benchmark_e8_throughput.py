import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time
import platform
import numpy as np
from core.mesh.router import E8RootDispatcher, SovereignMeshRouter

def benchmark_e8_dispatcher(iterations: int = 10000, batch_size: int = 256):
    dispatcher = E8RootDispatcher()
    router = SovereignMeshRouter(node_id="BENCHMARK-NODE")
    queue_depths = np.zeros(240, dtype=float)

    print("==========================================================")
    print(f"🚀 E8 ROOT DISPATCHER PERFORMANCE BENCHMARK (ARM64)")
    print(f"   Architecture : {platform.machine()} | Python: {platform.python_version()}")
    print(f"   Iterations   : {iterations:,} single bursts | Batch: {batch_size}")
    print("==========================================================")

    # Pre-generate telemetry vectors to isolate projection overhead
    rng = np.random.default_rng(42)
    telemetry_samples = rng.normal(loc=[4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002], scale=0.05, size=(iterations, 8))
    telemetry_samples[:, 7] = np.clip(telemetry_samples[:, 7], -0.005, 0.005)

    # 1. Warm-up (clamped to available sample size)
    warmup_count = min(500, iterations)
    for i in range(warmup_count):
        dispatcher.compute_dispatch_weights(telemetry_samples[i], queue_depths)

    # 2. Sequential Single-Burst Latency Benchmark
    latencies_us = []
    t_start_seq = time.perf_counter()
    
    for i in range(iterations):
        t0 = time.perf_counter_ns()
        weights = dispatcher.compute_dispatch_weights(telemetry_samples[i], queue_depths)
        _ = int(np.argmax(weights))
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)

    t_end_seq = time.perf_counter()
    total_time_seq = max(t_end_seq - t_start_seq, 1e-9)
    seq_throughput = iterations / total_time_seq

    p50 = np.percentile(latencies_us, 50)
    p95 = np.percentile(latencies_us, 95)
    p99 = np.percentile(latencies_us, 99)

    print(f"\n[1] Sequential Single-Burst Latency:")
    print(f"    Throughput : {seq_throughput:,.1f} dispatches/sec")
    print(f"    p50 Latency: {p50:.2f} µs")
    print(f"    p95 Latency: {p95:.2f} µs")
    print(f"    p99 Latency: {p99:.2f} µs")
    print(f"    Mean       : {np.mean(latencies_us):.2f} µs")

    # 3. Vectorized Matrix Projection Throughput (Batch SIMD)
    num_batches = max(1, iterations // batch_size)
    actual_batch_items = num_batches * batch_size
    if actual_batch_items <= iterations:
        batch_data = telemetry_samples[:actual_batch_items].reshape((num_batches, batch_size, 8))
        
        t_start_batch = time.perf_counter()
        for b in range(num_batches):
            _ = np.dot(batch_data[b], dispatcher.roots.T)

        t_end_batch = time.perf_counter()
        total_time_batch = max(t_end_batch - t_start_batch, 1e-9)
        batch_throughput = actual_batch_items / total_time_batch

        print(f"\n[2] Vectorized BLAS / NEON Projection:")
        print(f"    Batch Size : {batch_size}")
        print(f"    Throughput : {batch_throughput:,.1f} vector projections/sec")

    # 4. End-to-End Router Lifecycle (Gates + Dispatch + History + Decay)
    t_start_e2e = time.perf_counter()
    for i in range(iterations):
        router.route_burst(telemetry_samples[i], budget_sats=500)
    t_end_e2e = time.perf_counter()
    total_time_e2e = max(t_end_e2e - t_start_e2e, 1e-9)
    e2e_throughput = iterations / total_time_e2e

    print(f"\n[3] Full Router Lifecycle (3 Safety Gates + Ledger Prep):")
    print(f"    Throughput : {e2e_throughput:,.1f} full cycles/sec")
    print(f"    Mean Time  : {(total_time_e2e / iterations) * 1e6:.2f} µs/burst")
    print("==========================================================\n")

if __name__ == "__main__":
    benchmark_e8_dispatcher(iterations=10000, batch_size=256)
