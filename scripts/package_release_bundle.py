#!/usr/bin/env python3
"""
package_release_bundle.py - Sovereign Appliance Release Packager
Packages CURRENT_STATE.json, audit journal, scaling results, and case study
into a signed, cryptographically attested release tarball.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from verify_journal_integrity import audit_journal

BASE_DIR = os.path.expanduser("~/Tordial-GS")
JOURNAL_PATH = os.path.expanduser("~/.sovereign_audit_journal.jsonl")
RELEASES_DIR = os.path.join(BASE_DIR, "releases")

TARGET_FILES = {
    "CURRENT_STATE.json": os.path.join(BASE_DIR, "CURRENT_STATE.json"),
    "scaling_results.json": os.path.join(BASE_DIR, "scaling_results.json"),
    "SOVEREIGN_EVALUATION_CASE_STUDY.md": os.path.join(BASE_DIR, "docs", "SOVEREIGN_EVALUATION_CASE_STUDY.md"),
    "sovereign_audit_journal.jsonl": JOURNAL_PATH
}

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def package():
    os.makedirs(RELEASES_DIR, exist_ok=True)

    # 1. Read current state to retrieve sequence id
    try:
        with open(TARGET_FILES["CURRENT_STATE.json"], "r") as f:
            state = json.load(f)
            seq_id = state.get("last_sequence_id", 0)
    except Exception:
        seq_id = "unknown"

    release_tag = f"sovereign-appliance-seq{seq_id}-{int(time.time())}"
    staging_dir = os.path.join(RELEASES_DIR, release_tag)
    os.makedirs(staging_dir, exist_ok=True)

    print("[*] Pre-flight Check: Verifying cryptographic journal integrity...")
    if not audit_journal(JOURNAL_PATH):
        print("[-] RELEASE ABORTED: Audit journal failed cryptographic integrity verification.")
        sys.exit(1)
    print("[+] Pre-flight Check: Journal cryptographic integrity verified.")

    print(f"[*] Staging artifacts for release: {release_tag}")

    manifest_lines = []
    # 2. Copy and hash files
    for name, src in TARGET_FILES.items():
        if not os.path.exists(src):
            print(f"[-] WARNING: Missing artifact: {src}")
            continue
        dest = os.path.join(staging_dir, name)
        shutil.copy2(src, dest)
        digest = sha256_file(dest)
        manifest_lines.append(f"{digest}  {name}\n")
        print(f"  -> {name} [SHA256: {digest[:16]}...]")

    # 3. Write SHA256 manifest
    manifest_path = os.path.join(staging_dir, "MANIFEST.sha256")
    with open(manifest_path, "w") as f:
        f.writelines(manifest_lines)
    print(f"[+] Written manifest: {manifest_path}")

    # 4. Generate OpenSSL detached attestation signature
    sig_key = os.path.join(RELEASES_DIR, "release_attestation.key")
    cert_file = os.path.join(RELEASES_DIR, "release_attestation.crt")
    
    if not os.path.exists(sig_key):
        print("[*] Generating local release signing key and attestation cert...")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", sig_key, "-out", cert_file,
            "-days", "365", "-nodes",
            "-subj", "/CN=Sovereign-Evaluation-Appliance-Release-Signer"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sig_path = os.path.join(staging_dir, "MANIFEST.sha256.sig")
    subprocess.run([
        "openssl", "dgst", "-sha256", "-sign", sig_key,
        "-out", sig_path, manifest_path
    ], check=True)
    
    # Copy public cert to release payload for independent verification
    shutil.copy2(cert_file, os.path.join(staging_dir, "release_attestation.crt"))
    print("[+] Cryptographic attestation signature generated.")

    # 5. Build tarball
    archive_path = os.path.join(RELEASES_DIR, f"{release_tag}.tar.gz")
    with tarfile.open(archive_path, "w:gz") as tar:
        for item in os.listdir(staging_dir):
            tar.add(os.path.join(staging_dir, item), arcname=os.path.join(release_tag, item))

    # Clean staging directory
    shutil.rmtree(staging_dir)

    print(f"\n[+] RELEASE BUNDLE EXPORTED: {archive_path}")
    print(f"    Size: {os.path.getsize(archive_path)} bytes")
    print(f"    Archive SHA256: {sha256_file(archive_path)}")

    # 6. Verify signature
    pubkey = os.path.join(RELEASES_DIR, "release_attestation.crt")
    verify_cmd = [
        "openssl", "dgst", "-sha256",
        "-verify", pubkey,
        "-signature", sig_path
    ]
    # Extract manifest and sig temporarily for local verification check
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=RELEASES_DIR, members=[
            tar.getmember(f"{release_tag}/MANIFEST.sha256"),
            tar.getmember(f"{release_tag}/MANIFEST.sha256.sig"),
            tar.getmember(f"{release_tag}/release_attestation.crt")
        ])
    
    check_dir = os.path.join(RELEASES_DIR, release_tag)
    pubkey_path = os.path.join(check_dir, "pubkey.pem")
    subprocess.run([
        "openssl", "x509", "-pubkey", "-noout",
        "-in", os.path.join(check_dir, "release_attestation.crt")
    ], stdout=open(pubkey_path, "w"), check=True)

    verify_res = subprocess.run([
        "openssl", "dgst", "-sha256",
        "-verify", pubkey_path,
        "-signature", os.path.join(check_dir, "MANIFEST.sha256.sig"),
        os.path.join(check_dir, "MANIFEST.sha256")
    ], capture_output=True, text=True)

    shutil.rmtree(check_dir)

    if verify_res.returncode == 0:
        print("[+] Signature Verification: PASSED (Verified OK)")
    else:
        print(f"[-] Signature Verification: FAILED: {verify_res.stderr}")

if __name__ == "__main__":
    package()
