#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
import urllib.request
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment
from xrpl.transaction import submit_and_wait

RPC_URL = os.getenv("XRPL_RPC_URL", "https://xrplcluster.com")
TARGET_WALLET = os.getenv("XRPL_PRODUCTION_WALLET", "rfiRnMAXdfbAuXouJquX49VmxvHcDEgrB2")
NODE_ENDPOINT = os.getenv("NODE_ENDPOINT", "http://127.0.0.1:8080/api/v1/e8/dispatch")

def execute_paid_burst(client_seed: str = None, drops: int = 500, mock_onchain: bool = False):
    if not client_seed or client_seed.startswith("TORDIAL-") or "-" in client_seed:
        sender_wallet = Wallet.create()
        print(f"[*] Generated ephemeral client wallet: {sender_wallet.classic_address}")
        mock_onchain = True
    else:
        try:
            sender_wallet = Wallet.from_seed(client_seed)
            print(f"[*] Using supplied client wallet: {sender_wallet.classic_address}")
        except Exception as e:
            print(f"[!] Invalid seed provided ({e}), generating ephemeral wallet...")
            sender_wallet = Wallet.create()
            mock_onchain = True

    tx_hash = f"SIM_XRPL_{sender_wallet.classic_address[:8]}_{int(time.time()*1000)}"

    if not mock_onchain:
        print(f"[*] Submitting {drops} drops on XRPL to {TARGET_WALLET}...")
        try:
            client = JsonRpcClient(RPC_URL)
            payment = Payment(
                account=sender_wallet.classic_address,
                destination=TARGET_WALLET,
                amount=str(drops)
            )
            res = submit_and_wait(payment, client, sender_wallet)
            tx_hash = res.result.get("hash", tx_hash)
            engine_result = res.result.get("meta", {}).get("TransactionResult", "tesSUCCESS")
            print(f"[+] XRPL Settlement Result: {engine_result} | Hash: {tx_hash}")
        except Exception as e:
            print(f"[!] XRPL On-chain settlement error ({e}). Falling back to local mesh relay...")

    # Dispatch to local E8 mesh node
    payload = {
        "budget_sats": drops,
        "tx_hash": tx_hash,
        "queue_size": 2.0,
        "grad_temp": 1.5,
        "coherence": 0.999
    }

    req = urllib.request.Request(
        NODE_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[+] Mesh dispatch confirmed: HTTP {resp.status}")
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch paid mesh burst")
    parser.add_argument("--amount", type=int, default=500, help="Burst amount in sats/drops")
    parser.add_argument("--seed", type=str, default=None, help="XRPL secret seed (optional)")
    parser.add_argument("--mock", action="store_true", help="Bypass on-chain XRPL payment and simulate tx hash")
    args = parser.parse_args()

    execute_paid_burst(client_seed=args.seed, drops=args.amount, mock_onchain=args.mock)
