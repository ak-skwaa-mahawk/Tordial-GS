#!/usr/bin/env python3
import os
import sys
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo

RPC_URL = os.getenv("XRPL_RPC_URL", "https://xrplcluster.com")
TARGET_WALLET = os.getenv("XRPL_PRODUCTION_WALLET", "rfiRnMAXdfbAuXouJquX49VmxvHcDEgrB2")

client = JsonRpcClient(RPC_URL)

def check_balance():
    print(f"[*] Querying XRPL Mainnet ({RPC_URL}) for {TARGET_WALLET}...")
    try:
        req = AccountInfo(account=TARGET_WALLET, ledger_index="validated")
        res = client.request(req)
        if res.is_successful():
            account_data = res.result.get("account_data", {})
            drops = int(account_data.get("Balance", 0))
            xrp = drops / 1_000_000.0
            print("=" * 60)
            print("💎 XRPL MAINNET ACCOUNT STATUS: ACTIVE")
            print("=" * 60)
            print(f"Address          : {TARGET_WALLET}")
            print(f"Balance (XRP)    : {xrp:.6f} XRP")
            print(f"Balance (Drops)  : {drops:,} drops")
            print(f"Sequence         : {account_data.get('Sequence')}")
            print("=" * 60)
        else:
            error = res.result.get("error", "Unknown")
            if error == "actNotFound":
                print("=" * 60)
                print("⚠️  XRPL MAINNET ACCOUNT STATUS: INACTIVE (UNFUNDED)")
                print("=" * 60)
                print(f"Address          : {TARGET_WALLET}")
                print("Note             : Send >= 1 XRP to activate this account on-chain.")
                print("=" * 60)
            else:
                print(f"❌ Error: {error}")
    except Exception as e:
        print(f"❌ Connection/RPC Error: {e}")

if __name__ == "__main__":
    check_balance()
