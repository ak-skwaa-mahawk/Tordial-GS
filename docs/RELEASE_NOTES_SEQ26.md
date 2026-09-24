# Technical Release Notes: Sovereign Appliance Release `seq26-1790290767`

**Release Tag**: `sovereign-appliance-seq26-1790290767`  
**Tarball Archive**: `sovereign-appliance-seq26-1790290767.tar.gz`  
**Archive SHA-256**: `c1778eecf8349aaf3ac3508164a7ee308769fef474b48ed71b4a48c75b4c1f26`  
**Signer Attestation**: RSA-4096 / SHA-256 (`release_attestation.crt`)  
**Verification Verdict**: `Signature Verification: PASSED (Verified OK)`

---

## 1. Cryptographic Manifest & Artifact Attestation

Every component within the release package is locked to a SHA-256 digest in `MANIFEST.sha256` and authenticated via detached OpenSSL RSA signature (`MANIFEST.sha256.sig`). The table below maps each attested file to its verified architectural guarantee documented in `docs/SOVEREIGN_EVALUATION_CASE_STUDY.md`:

| Artifact Name | Truncated SHA-256 Digest | Case Study Section | Architectural Guarantee & Verification Claim |
|---|---|---|---|
| **`sovereign_audit_journal.jsonl`** | `e9e4908afddeef02...` | **§6 & §7** Audit State & Real-Time Telemetry | Proves monotonic hash progression through Sequence ID 26 (`de154802...`). Demonstrates cryptographic chaining integrity ($H_n = \text{SHA256}(H_{n-1} \parallel \dots)$) across 400 continuous evaluation cycles without state forks. |
| **`scaling_results.json`** | `d96ccbb497e69429...` | **§8** Multi-Node Q16.16 Inference Scaling Profile | Contains empirical benchmarks sweeping batch nodes $n = 1 \dots 8$ (50 frames/node). Proves $O(n)$ fixed-point linear scaling where median latency remains bounded within $[78.95, 87.04]\text{ ms}$ and throughput holds at $10.8 \pm 0.4\text{ fps}$. |
| **`CURRENT_STATE.json`** | `6ae1103d69e8c83b...` | **§8 & §9** Operational Baseline & Remote Uplink | Establishes the authoritative state record for Sequence 26: confirms active ports (`COM2 :9998`, UDP `:9999`, WS `:8765`), telemetry pipeline status (`VERIFIED_ALERT_DISPATCH`), and outbound TLS/WSS remote relay status (`VERIFIED_AUTHENTICATED_STREAMING`). |
| **`SOVEREIGN_EVALUATION_CASE_STUDY.md`** | `6f5249b4017150d8...` | **§1 – §9** Entire System Specification | Canonical specification defining the formal invariants ($n < \text{node\_count} \land n < \text{MAX\_NODES}$), little-endian wire framing (`SOVA_MAGIC = 0x534F5641`), non-colliding authority bitmasks, and isolated microkernel architecture. |

---

## 2. Direct Mapping to Case Study Claims

### A. Non-Colliding Authority Flags & In-Kernel Anomaly Classification (§5 & §7)
* **Architectural Claim**: The evaluation engine must isolate authority and anomaly flags, transitioning between baseline certification (`0x0001`, `SOVR_FLAG_STATUTORY_DUTY`) and critical alarm (`0x0009`, asserting bit 3 `0x0008`, `SOVR_FLAG_ANOMALY_DETECTED`) without bitmask corruption or corporate defense leakage (`0x0002`, `0x0004`).
* **Digest Evidence (`sovereign_audit_journal.jsonl`)**: Line entries for Sequence 24–26 explicitly confirm `raw: 9` with `corporate_defense_valid: false` and `can_be_administered_away: false`. The binary response parser (`mesh_bridge_daemon.py`) correctly routes `raw: 9` to WebSocket `:8765` as an alert level of `CRITICAL`.

### B. Bounded Multi-Node Scaling Ceiling (§8)
* **Architectural Claim**: Fixed-point Q16.16 neural execution performs bounded integer-only dot products and activations that do not degrade interrupt-driven UART responsiveness as the graph node count scales from 1 to 8.
* **Digest Evidence (`scaling_results.json`)**:
  - $n = 1$: Throughput $10.55\text{ fps}$, Median Latency $80.37\text{ ms}$, P95 $132.13\text{ ms}$.
  - $n = 4$: Throughput $10.99\text{ fps}$, Median Latency $80.90\text{ ms}$, P95 $119.78\text{ ms}$.
  - $n = 8$: Throughput $10.98\text{ fps}$, Median Latency $79.83\text{ ms}$, P95 $114.90\text{ ms}$.
  The data proves that CPU execution overhead is negligible compared to physical UART frame transfer windows.

### C. Authenticated Outbound TLS/WSS Uplink (§9)
* **Architectural Claim**: Telemetry emitted to local UDP port `:9999` must bridge to remote aggregators via authenticated WSS using an asynchronous backpressure queue (`maxsize=1024`), preserving local delivery even when remote networks fail.
* **Digest Evidence (`CURRENT_STATE.json`)**:
  - `uplink_relay.protocol`: `"TLS/WSS"`
  - `uplink_relay.auth_scheme`: `"Bearer Token"`
  - `uplink_relay.outbound_queue_size`: `1024`
  - `uplink_relay.status`: `"VERIFIED_AUTHENTICATED_STREAMING"`
  Directly reflects the clean pass executed in `test_uplink_relay.py` where Bearer tokens (`SOVEREIGN_UPLINK_AUTH_KEY_V1`) were enforced over self-signed TLS channels.

---

## 3. Independent Verification Procedure

External security auditors can independently verify the authenticity and integrity of the release bundle using OpenSSL:

```bash
# 1. Extract the release bundle
tar -xzvf sovereign-appliance-seq26-1790290767.tar.gz
cd sovereign-appliance-seq26-1790290767

# 2. Extract public key from the bundled attestation certificate
openssl x509 -pubkey -noout -in release_attestation.crt > pubkey.pem

# 3. Verify detached cryptographic signature against MANIFEST.sha256
openssl dgst -sha256 -verify pubkey.pem -signature MANIFEST.sha256.sig MANIFEST.sha256
# Expected Output: Verified OK

# 4. Verify all individual artifact digests
sha256sum -c MANIFEST.sha256
# Expected Output:
# CURRENT_STATE.json: OK
# scaling_results.json: OK
# SOVEREIGN_EVALUATION_CASE_STUDY.md: OK
# sovereign_audit_journal.jsonl: OK

