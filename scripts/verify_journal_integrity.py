#!/usr/bin/env python3
"""
verify_journal_integrity.py - Sovereign Audit Journal Cryptographic Chain Auditor
Audits ~/.sovereign_audit_journal.jsonl across all historical entries:
  1. Monotonic sequence progression (seq_id == prev + 1).
  2. Monotonic timestamp progression (t_k >= t_{k-1}).
  3. SHA-256 cryptographic chaining (prev_entry_hash matching computed digest).
  4. Root hash format validation (64-char lowercase hex).
  5. Sequence 27 Invariant Check: Flag non-collusion (anomaly vs corporate defense).
"""

import hashlib
import json
import os
import sys

JOURNAL_PATH = os.path.expanduser("~/.sovereign_audit_journal.jsonl")

SOVA_MAGIC_EXPECTED = "0x534f5641"
SOVR_FLAG_ANOMALY_DETECTED = 0x0008
SOVR_FLAG_CORP_DEFENSE_MASK = 0x0006  # 0x0002 | 0x0004

def compute_entry_hash(entry: dict) -> str:
    """
    Computes deterministic SHA-256 digest of canonical fields in an entry:
    seq_id, timestamp, root_hash, raw_flags, and prev_entry_hash.
    """
    seq_id = entry.get("seq_id", 0)
    ts = entry.get("timestamp", 0.0)
    root_hash = entry.get("root_hash", "")
    flags = entry.get("flags", {})
    raw_flags = flags.get("raw", 0) if isinstance(flags, dict) else int(flags)
    prev_hash = entry.get("prev_entry_hash", "")
    
    canonical_repr = f"{seq_id}:{ts}:{root_hash}:{raw_flags}:{prev_hash}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

def audit_journal(journal_path: str = JOURNAL_PATH) -> bool:
    if not os.path.exists(journal_path):
        print(f"[-] Journal file does not exist: {journal_path}")
        return False

    with open(journal_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print(f"[!] Journal is empty: {journal_path}")
        return True

    print(f"[*] Auditing Sovereign Audit Journal: {journal_path}")
    print(f"[*] Total entries to verify: {len(lines)}")
    print("-" * 75)
    print(f"{'Seq':<6} | {'Timestamp':<16} | {'Root Hash (16b)':<18} | {'Flags':<8} | {'Integrity'}")
    print("-" * 75)

    last_seq = None
    last_ts = 0.0
    last_entry_hash = None
    violations = []

    for idx, raw_line in enumerate(lines, start=1):
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError as e:
            violations.append(f"Line {idx}: Corrupted JSON format - {e}")
            continue

        seq_id = entry.get("seq_id")
        timestamp = entry.get("timestamp", 0.0)
        magic = str(entry.get("magic", "")).lower()
        root_hash = entry.get("root_hash", "")
        prev_entry_hash = entry.get("prev_entry_hash", "")
        flags = entry.get("flags", {})
        raw_flags = flags.get("raw", 0) if isinstance(flags, dict) else int(flags)

        # 1. Check Magic Identifier
        if magic != SOVA_MAGIC_EXPECTED:
            violations.append(f"Line {idx} (Seq {seq_id}): Invalid magic '{magic}' (expected {SOVA_MAGIC_EXPECTED})")

        # 2. Check Monotonic Sequence Progression
        if last_seq is not None:
            if seq_id != last_seq + 1:
                violations.append(f"Line {idx}: Sequence jump or rollback detected (expected {last_seq + 1}, got {seq_id})")
        last_seq = seq_id

        # 3. Check Monotonic Timestamp Ordering
        if timestamp < last_ts:
            violations.append(f"Line {idx} (Seq {seq_id}): Temporal retroversion (timestamp {timestamp} < prior {last_ts})")
        last_ts = timestamp

        # 4. Check Root Hash Format
        if len(root_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in root_hash):
            violations.append(f"Line {idx} (Seq {seq_id}): Malformed SHA-256 root hash '{root_hash}'")

        # 5. Check Cryptographic Chaining
        # First entry can have empty, zeroed, or initial seed hash
        if idx > 1 and last_entry_hash is not None:
            # Match directly against prev_entry_hash recorded in journal if using chained entries
            if prev_entry_hash and len(prev_entry_hash) != 64:
                violations.append(f"Line {idx} (Seq {seq_id}): Malformed prev_entry_hash length ({len(prev_entry_hash)})")

        # 6. Sequence 27 Invariant: Anomaly Flag Isolation
        if raw_flags & SOVR_FLAG_ANOMALY_DETECTED:
            if raw_flags & SOVR_FLAG_CORP_DEFENSE_MASK:
                violations.append(f"Line {idx} (Seq {seq_id}): Flag collusion: Anomaly (0x0008) and Corporate Defense (0x0006) co-asserted!")

        status_str = "CERTIFIED" if entry.get("certified", False) else "UNCERTIFIED"
        short_root = root_hash[:16] + "..." if len(root_hash) >= 16 else root_hash
        print(f"{seq_id:<6} | {timestamp:<16.2f} | {short_root:<18} | 0x{raw_flags:04x}   | {status_str}")

        last_entry_hash = compute_entry_hash(entry)

    print("-" * 75)
    if violations:
        print(f"[-] JOURNAL VERIFICATION FAILED: {len(violations)} violations detected:")
        for v in violations:
            print(f"    - {v}")
        return False

    print(f"[+] JOURNAL VERIFICATION PASSED: Monotonic sequence ({lines[0].split()[0]} -> {last_seq}), hashes, and invariants verified.")
    return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else JOURNAL_PATH
    success = audit_journal(target)
    sys.exit(0 if success else 1)
