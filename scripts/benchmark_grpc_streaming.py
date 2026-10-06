#!/usr/bin/env python3
"""
gRPC transport benchmark: Unary RouteBurst vs Bidirectional StreamRouteBursts.
Measures round-trip throughput (ops/sec) and latency percentiles (p50, p95, p99)
over 1,000 operational telemetry frames.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time
import platform
import numpy as np
import grpc
from concurrent import futures

from core.mesh import router_pb2, router_pb2_grpc
from core.mesh.grpc_server import SovereignMeshServicer


def run_benchmark(iterations: int = 1000):
    print("==========================================================")
    print("⚡ gRPC TRANSPORT BENCHMARK: UNARY vs STREAMING")
    print(f"   Architecture : {platform.machine()} | Python: {platform.python_version()}")
    print(f"   Sample Size  : {iterations:,} dispatches per transport mode")
    print("==========================================================")

    # 1. Spin up ephemeral server on loopback
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    router_pb2_grpc.add_SovereignMeshServiceServicer_to_server(
        SovereignMeshServicer(node_id="BENCHMARK-NODE"), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    stub = router_pb2_grpc.SovereignMeshServiceStub(channel)

    # Pre-generate 1,000 calibrated requests
    requests = []
    for i in range(iterations):
        telemetry = router_pb2.TelemetryVector(
            latency_ms=4.0 + (i % 50) * 0.01,
            queue_depth=3.0,
            thermal_headroom=0.01,
            battery_reserve=0.02,
            packet_loss_rate=3.5,
            bandwidth_capacity=0.98,
            memory_pressure=0.2,
            compute_load=0.002,
        )
        req = router_pb2.RouteBurstRequest(
            origin_node_id=f"CLIENT-{i}",
            telemetry=telemetry,
            budget_sats=500,
        )
        requests.append(req)

    # ---------------------------------------------------------
    # Warmup
    # ---------------------------------------------------------
    for _ in range(50):
        _ = stub.RouteBurst(requests[0])

    # ---------------------------------------------------------
    # Benchmark 1: Unary RouteBurst
    # ---------------------------------------------------------
    latencies_unary = []
    t0_unary = time.perf_counter()
    for req in requests:
        start_ns = time.perf_counter_ns()
        resp = stub.RouteBurst(req)
        end_ns = time.perf_counter_ns()
        latencies_unary.append((end_ns - start_ns) / 1000.0)
    t1_unary = time.perf_counter()

    unary_elapsed = t1_unary - t0_unary
    unary_throughput = iterations / unary_elapsed

    # ---------------------------------------------------------
    # Benchmark 2: Bidirectional StreamRouteBursts
    # ---------------------------------------------------------
    def request_generator():
        for r in requests:
            yield r

    latencies_stream = []
    t0_stream = time.perf_counter()
    response_stream = stub.StreamRouteBursts(request_generator())

    for _ in range(iterations):
        start_ns = time.perf_counter_ns()
        resp = next(response_stream)
        end_ns = time.perf_counter_ns()
        latencies_stream.append((end_ns - start_ns) / 1000.0)
    t1_stream = time.perf_counter()

    stream_elapsed = t1_stream - t0_stream
    stream_throughput = iterations / stream_elapsed

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------
    server.stop(0)
    channel.close()

    # ---------------------------------------------------------
    # Metrics Reporting
    # ---------------------------------------------------------
    speedup = stream_throughput / max(unary_throughput, 1e-9)

    print(f"\n| Transport Mode               | Throughput (ops/s) | p50 (µs) | p95 (µs) | p99 (µs) | Total Elapsed (ms) |")
    print(f"|------------------------------|--------------------|----------|----------|----------|--------------------|")
    print(f"| Unary RouteBurst             | {unary_throughput:>18,.1f} | {np.percentile(latencies_unary, 50):>8.2f} | {np.percentile(latencies_unary, 95):>8.2f} | {np.percentile(latencies_unary, 99):>8.2f} | {unary_elapsed * 1000:>18.2f} |")
    print(f"| StreamRouteBursts (Duplex)   | {stream_throughput:>18,.1f} | {np.percentile(latencies_stream, 50):>8.2f} | {np.percentile(latencies_stream, 95):>8.2f} | {np.percentile(latencies_stream, 99):>8.2f} | {stream_elapsed * 1000:>18.2f} |")
    print("==========================================================")
    print(f"🚀 Streaming Throughput Advantage: {speedup:.2f}x faster throughput\n")


if __name__ == "__main__":
    run_benchmark(iterations=1000)
