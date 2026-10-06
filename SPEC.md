# Tordial-GS: Low-Latency Heterogeneous Edge Mesh

## Overview
Tordial-GS is an ARM64-native routing and settlement layer designed to coordinate local autonomous edge agents across constrained devices without external cloud dependencies.

## Core Primitives
1. **8D State-Space Router**: Uses vectorized projection across an 8-dimensional operational metric (latency, queue depth, thermal state, battery level, packet loss, bandwidth, memory pressure, compute load) to select optimal peer routes in ~25 µs.
2. **Thermal Governor**: Integrates with hardware sensors to dynamically scale back dispatch rates before hardware thermal throttling occurs.
3. **Decentralized Settlement Journal**: Appends verifiable micro-transactions locally with a monotonic hash chain, guaranteeing conservation of accounting balances.

## Verified Baselines (ARM64 Native)
- **Sequential Dispatch Latency**: 12.81 µs (p50), 20.94 µs (p99)
- **Batch SIMD Vector Projections**: 1,424,314.7 projections/sec
- **Full Router Lifecycle Throughput**: 39,794.3 full cycles/sec (25.13 µs/burst)
- **Settlement Verification**: 2,500 settled transactions audited; 10.0% floor reserve conserved.

## Comparative Benchmark Analysis (ARM64 Native)
Measured across 10,000 routing evaluations over 240 candidate edge nodes:

| Strategy | Throughput (ops/s) | p50 Latency (µs) | p99 Latency (µs) | Telemetry Awareness |
|---|---|---|---|---|
| **Weighted Round-Robin (WRR)** | 1,518,422.8 | 0.26 | 0.36 | None (Static / 1D) |
| **Kademlia XOR Metric (240 N)** | 25,763.4 | 38.07 | 48.23 | None (Topology Only) |
| **E8 State-Space Dispatcher** | **68,447.0** | **14.58** | **17.81** | **8D Continuous Dynamic** |

### Key Takeaway
Vectorized matrix projection against the root lattice allows `Tordial-GS` to evaluate full 8D operational telemetry (thermal, queue pressure, link loss, and memory) faster than linear bitwise XOR distance calculations over the same candidate peer set.

## gRPC Transport Performance Profile (ARM64 Loopback)
Measured over 1,000 operational telemetry frames across the `SovereignMeshService` contract:

| Transport Mode | Throughput (ops/s) | p50 Latency (µs) | p95 Latency (µs) | p99 Latency (µs) | Total Time (1k frames) |
|---|---|---|---|---|---|
| **Unary `RouteBurst`** | 205.9 | 5,336.61 | 7,133.90 | 10,673.18 | 4,857.12 ms |
| **Duplex `StreamRouteBursts`** | **521.6** | **1,311.28** | **5,373.88** | **9,695.54** | **1,917.02 ms** |

### Streaming Advantage
Persistent HTTP/2 stream multiplexing via `StreamRouteBursts` provides a **2.53× throughput increase** and cuts median end-to-end routing latency from $5.34\ \text{ms}$ down to $1.31\ \text{ms}$, making it the required transport mode for real-time edge telemetry feeds.

## High-Throughput Edge Client Benchmarks (`isst_toft_mesh`)

### Protocol: Native Rust HTTP/2 Duplex Stream (`tonic`)
* **Transport**: Direct HTTP/2 Duplex Streaming via `SovereignMeshService/StreamRouteBursts`
* **Test Node**: `EDGE-GRPC-01` / `RUST-EDGE-xxxx`
* **Frame Sample**: 1,000 continuous frames pipelined via `tokio::sync::mpsc`
* **Target Endpoint**: `127.0.0.1:50055`


eof
