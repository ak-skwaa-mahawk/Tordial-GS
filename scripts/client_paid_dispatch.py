#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment
from xrpl.transaction import submit_and_wait

RPC_URL = os.getenv("XRPL_RPC_URL", "https://xrplcluster.com")
TARGET_WALLET = os.getenv("XRPL_PRODUCTION_WALLET", "rfiRnMAXdfbAuXouJquX49VmxvHcDEgrB2")
NODE_ENDPOINT = "http://127.0.0.1:8080/api/v1/e8/dispatch"

def execute_paid_burst(client_seed: str, drops: int = 500):
    client = JsonRpcClient(RPC_URL)
    sender_wallet = Wallet.from_seed(client_seed)
    
    print(f"[*] Submitting {drops} drops on XRPL from {sender_wallet.classic_address} to {TARGET_WALLET}...")
    payment = Payment(
        account=sender_wallet.classic_address,
        destination=TARGET_WALLET,
        amount=str(drops)
    )
    
    res = submit_and_wait(payment, client, sender_wallet)
    tx_hash = res.result.get("hash")
    engine_result = res.result.get("meta", {}).get("TransactionResult")
    
    if engine_result != "tesSUCCESS":
        print(f"❌ Payment failed: {engine_result}")
        return
        
    print(f"✅ [PAID ON-CHAIN]: Hash={tx_hash}")
    
    # Send authenticated compute request with transaction hash
    req_body = json.dumps({
        "require_payment": True,
        "xrpl_tx_hash": tx_hash,
        "budget_sats": drops,
        "queue_size": 4.2,
        "coherence": 0.995
    }).encode("utf-8")
    
    req = urllib.request.Request(
        NODE_ENDPOINT,
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("\n🚀 [E8 MANIFOLD DISPATCH CONFIRMED]")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/client_paid_dispatch.py <CLIENT_SENDER_SEED> [DROPS]")
    else:
        seed = sys.argv[1]
        drops = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        execute_paid_burst(seed, drops)
