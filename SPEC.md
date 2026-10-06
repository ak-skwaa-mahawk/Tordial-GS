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
