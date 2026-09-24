# Technical Release Notes: Sovereign Appliance Release `seq27`

**Milestone**: Sequence 27 Anti-Replay Hardening & Monotonic State Progression  
**Ledger Baseline**: Sequence ID 27 (`status_code: 0xe002`, `certified: false`, zeroed root hash)  
**Security Reference**: `docs/THREAT_MODEL_SEQ27.md` (Threat 3: Replay & Out-of-Sequence Ledger Injection)  
**Integrity Status**: 27 / 27 Entries Formally Audited & Chained (`verify_journal_integrity.py` PASSED)

---

## 1. Architectural Changes & Wire Protocol Update

To eliminate replay attacks (CWE-294) and sequence retroversion vulnerabilities, the binary audit wire protocol was modified across C and Python domains:

* **Struct Layout Extension**: Added a 64-bit unsigned monotonic sequence counter (`uint64_t sequence_id`) immediately following `fiduciary_role` (offset 8).
* **Frame Size Transition**: Packed `SovereignAuditFrame` (`sovereign_audit_frame_t`) expanded from 808 bytes to 816 bytes, preserving 64-bit alignment across GCC System V ABI boundaries.
* **Component Synchronization**:
  - `seL4-workspace`: Updated `libraries-3/sovereign_contract.h` and `apps/rootserver/verify/verify_harness.c`.
  - `Telephone_port`: Updated `audit_contract.py` (`ctypes.c_uint64`) and client evaluation harnesses (`test_anomaly.py`, `bench_scaling.py`, `test_replay.py`).

---

## 2. Adversarial Replay Test Execution (`test_replay.py`)

Adversarial stress validation was executed against the live seL4 interrupt-driven COM2 serial UART socket (`127.0.0.1:9998`):

### Phase 1: Forward Monotonic Progression
* **Payload**: `sequence_id = 27`, `fiduciary_role = 0xC001`, `node_count = 1`.
* **Verdict**: **ACCEPTED**
  - Status Code: `0x0000` (`SOVR_STATUS_SUCCESS`)
  - Authority Flags: `0x0006` (`SOVR_FLAG_CORP_DEFENSE_VALID | SOVR_FLAG_CAN_BE_ADMINISTERED`)
  - Kernel Log: `rootserver: [COM2 ACK] Certified frame. Status: 0x0000, Flags: 0x0006`

### Phase 2: Identical Duplicate Replay Attack
* **Payload**: Re-transmission of identical `sequence_id = 27`.
* **Verdict**: **REJECTED (CWE-294 Mitigated)**
  - Status Code: `0xe002` (`SOVR_STATUS_REJECT / INVALID`)
  - Flags: `0x0000` (all authority and fiduciary flags revoked)
  - Kernel Log: `rootserver: [COM2 REJECT] Invalid magic / Replay rejection`

### Phase 3: Retroverted Sequence Injection
* **Payload**: Historical backwards sequence frame `sequence_id = 26`.
* **Verdict**: **REJECTED**
  - Status Code: `0xe002`
  - Flags: `0x0000` (zero authority granted)
  - Nonce Order Invariant Preserved: Microkernel state head remained protected against retroversion.

---

## 3. Cryptographic Journal Progression & Chain Invariants

Following rejection of adversarial frames, an on-demand microkernel certification cycle sealed the transition into `~/.sovereign_audit_journal.jsonl`:

```json
{
  "certified": false,
  "flags": {
    "can_be_administered_away": false,
    "corporate_defense_valid": false,
    "raw": 0,
    "statutory_duty": false
  },
  "magic": "0x534f5641",
  "prev_entry_hash": "a1be72ec46d7b07cf0efe016da28eb5f37ab7151fb7a6b2872d7d448818d5e63",
  "root_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "seq_id": 27,
  "status_code": "0xe002",
  "timestamp": 1790291767.184605
}
​Zero-Root Invariant: When frame processing is rejected (0xe002), the certified root hash is securely zeroed out, preventing counterfeit certification propagation.
​Cryptographic Continuity: Entry 27 remains immutably bound to Entry 26 via prev_entry_hash (a1be72ec46...).
​Automated Audit: verify_journal_integrity.py confirmed 27 consecutive entries without sequence gaps, temporal retroversions, or flag collusion.
​4. Release Packager Pre-Flight Verification Gate
​The release packaging pipeline (scripts/package_release_bundle.py) now enforces automated pre-flight gating:
​verify_journal_integrity.py is invoked prior to staging artifacts.
​Any broken SHA-256 parent hash linkage or non-monotonic sequence ID immediately halts release tarball export with exit code 1.
​Valid releases generate detached OpenSSL RSA-4096 signatures (MANIFEST.sha256.sig) verified via pubkey.pem.
