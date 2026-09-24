# Case Study: Capability-Isolated TinyML Inference and Invariant Attestation on seL4

**Author / Maintainer:** ak-skwaa-mahawk  
**Target Platform:** x86_64 (PC99) / seL4 Microkernel / CAmkES Declarative Architecture  
**Core Components:** Freestanding Fixed-Point ML Runtime, IRQ 3 UART Ingestion, CBMC Model-Checked Serialization  

---

## 1. Executive Summary & Problem Space

Traditional edge deployments attach untrusted machine learning inference models directly to hardware sensor ingestion loops, exposing safety-critical systems to deep attack surfaces. Standard ML runtimes (TensorFlow Lite, ONNX, PyTorch) require standard C/C++ runtimes, POSIX wrappers, floating-point exception handling, and dynamic heap allocators—incompatibilities that violate formal microkernel baselines.

This work details the implementation and empirical evaluation of an end-to-end sovereign attestation appliance on the formally verified seL4 microkernel. The system achieves:
1. **Zero-I/O Capability Isolation**: An edge TinyML engine isolated within an execution domain with zero physical I/O descriptors, communicating exclusively over synchronous capability-gated IPC.
2. **Freestanding Fixed-Point Inference**: A pure Q16.16 inference engine compiled with `-ffreestanding -nostdlib`, eliminating FPU traps and dynamic allocation.
3. **Deterministic Interrupt Ingestion**: Interrupt-driven (COM2 IRQ 3) frame ingestion coupled to a cryptographic SHA-256 state engine maintaining a tamper-evident monotonic journal.

---

## 2. Formal Invariant Specification & Topology

### System Invariants
* **Spatial Memory Isolation ($\mathcal{I}_{VSpace}$)**: The inference runtime possesses no physical hardware capabilities ($c \notin \text{CSpace}(\mathcal{C}_{ML}) \ \forall \ c \in \{\text{IOPort}, \text{IRQ}, \text{DMA}\}$). Perturbations in tensor evaluations cannot corrupt device drivers or the rootserver.
* **Bounded Serial Execution ($\mathcal{I}_{Bound}$)**: Input frames are constrained to an 808-byte wire contract (`sovereign_audit_frame_t`). Frames with $\text{node\_count} > 8$ are rejected at the parsing boundary with `0xE003` (`SOVR_STATUS_ERR_BOUNDS`), verified up to unwind depth $k=64$ via CBMC.
* **Monotonic Chain Integrity ($\mathcal{I}_{Audit}$)**: Ledger sequence state satisfies $H_n = \text{SHA-256}(H_{n-1} \parallel \text{Frame}_n \parallel \text{Seq}_n)$.

### Capability Architecture

+-------------------------------------------------------------+
|                      seL4 Microkernel                       |
+--------------+-------------------------------+--------------+
|                               |
seL4_IRQHandler                 seL4_CNode
(COM2 Port 0x2f8)             (Sandboxed Heap)
|                               |
v                               v
+--------------------+           +-------------------+
|    COM2 Driver     |           |  TinyML Runtime   |
| (Physical Ingest)  |           |   (Zero I/O Cap)  |
+----------+---------+           +---------+---------+
|                               |
|       seL4 Synchronous IPC    |
+---------------v---------------+
|
+-----------------------+
|  Sovereign Rootserver |
|  (Freestanding SHA256)|
+-----------+-----------+
|
| UDP Burst (:9999)
v
+-----------------------+
|  Tordial-GS Gateway   |
|  (Monotonic Journal)  |
+-----------------------+

---

## 3. Toolchain & Runtime Engineering

1. **Freestanding Fixed-Point Arithmetic**:
   The inference loop executes a two-layer perceptron using pure integer operations (Q16.16 fixed-point math). Weights and bias tables are statically embedded in `.rodata`, eliminating heap calls and floating-point registers (`-mno-sse`, `-mno-mmx`).
2. **Build Target Decoupling in CAmkES/seL4 Tutorials**:
   Tutorial root-task frameworks hardcode target namespaces. Resolving target collisions between rootserver and module subdirectories was achieved by directly binding `target_sources(libraries-3 PRIVATE ...)` in CMake, removing the need for runtime memory-patching scripts.
3. **Automated Invariant Verification**:
   The bounded model checking harness (`verify_harness.c`) proved absence of out-of-bounds pointer dereferences and memory leaks under exhaustive symbolic input testing via CBMC, followed by 10,000 randomized state fuzzing cycles.

---

## 4. Empirical Performance Profile

Performance was measured across multiple sustained 100-frame burst runs over the physical COM2 loopback interface (808 bytes/frame) on x86_64 PC99 emulation:

| Benchmark Metric | Run 1 (100 Frames) | Run 2 (100 Frames) | Invariant Target | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Sustained Throughput** | 11.8 frames/sec | 11.2 frames/sec | $> 8.0$ frames/sec | **Verified** |
| **Effective Bandwidth** | 80.34 kbps | 76.27 kbps | Wire Saturation | **Verified** |
| **Latency Min** | 60.21 ms | 66.04 ms | $< 100$ ms | **Verified** |
| **Latency Median (P50)** | 75.32 ms | 77.02 ms | $< 90$ ms | **Verified** |
| **Latency P95** | 124.12 ms | 114.62 ms | $< 150$ ms | **Verified** |
| **Latency Max** | 133.88 ms | 134.27 ms | $< 200$ ms | **Verified** |
| **Frame Loss / Desync** | 0 / 100 (0.0%) | 0 / 100 (0.0%) | 0.0% | **Verified** |

Total roundtrip processing—encompassing interrupt line handling, user-space buffer ingest, fixed-point inference, SHA-256 root calculation, and serial response transmission—consistently completes with a median latency of ~76 ms.

---

## 5. Community & Upstream Significance

* **Feasibility of Bare-Metal Edge AI**: Machine learning inference does not require bloated Linux runtimes or micro-distributions. A strictly typed, freestanding C runtime can execute inference deterministically in high-assurance environments.
* **Formally Isolated AI Assurance**: By denying physical capabilities to the inference domain, the system eliminates adversarial model inputs as a threat vector against microkernel availability.

## 6. Multi-Node Batch Inference & Dynamic Anomaly Classification

* **Protocol Framing**: Bounded multi-node evaluation across $1 \le \text{node\_count} \le 8$ nodes within the 808-byte `sovereign_audit_frame_t`.
* **Zero-Collision Flag Bitmask**:
  - `SOVR_FLAG_STATUTORY_DUTY` (`0x0001`)
  - `SOVR_FLAG_CORP_DEFENSE_VALID` (`0x0002`)
  - `SOVR_FLAG_CAN_BE_ADMINISTERED` (`0x0004`)
  - `SOVR_FLAG_ANOMALY_DETECTED` (`0x0008`)
* **Empirical Anomaly Toggling**: Under calibrated Q16.16 weights, normal multi-node inputs evaluate deterministically to status `0x0000` / flags `0x0001`, while adversarial inputs trigger in-kernel flag transition to `0x0009` (`0x0001 | 0x0008`).
* **Verification Proofs**: Model checked via dual-mode harness (`verify_harness.c`):
  - Array bounds invariant: $n < \text{node\_count} \land n < \text{MAX\_NODES}$
  - Buffer copy bound: $\min(\text{sizeof}(feature\_buf), \text{sizeof}(node))$
  - 20,000 fuzz cycles with Address/UndefinedBehaviorSanitizers: 0 violations.
