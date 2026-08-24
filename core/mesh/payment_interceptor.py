import os
import logging
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import Tx

logger = logging.getLogger("payment_interceptor")

XRPL_MAINNET_URL = os.getenv("XRPL_RPC_URL", "https://xrplcluster.com")
PRODUCTION_TARGET_WALLET = os.getenv("XRPL_PRODUCTION_WALLET", "rYourRealWalletAddressHere")

client = JsonRpcClient(XRPL_MAINNET_URL)

def verify_xrpl_payment(tx_hash: str, required_drops: int, target_wallet: str = None) -> bool:
    """
    Validates on-chain settlement:
    1. Transaction is validated in a ledger.
    2. Result is tesSUCCESS.
    3. Destination matches your production address.
    4. Delivered amount meets or exceeds required drops.
    """
    destination_target = target_wallet or PRODUCTION_TARGET_WALLET
    if destination_target == "rYourRealWalletAddressHere":
        logger.warning("Production wallet not configured; rejecting payment check.")
        return False

    try:
        req = Tx(transaction=tx_hash)
        res = client.request(req)
        
        if not res.is_successful():
            return False
            
        data = res.result
        if not data.get("validated", False):
            return False
            
        meta = data.get("meta", {})
        if meta.get("TransactionResult") != "tesSUCCESS":
            return False
            
        tx = data.get("tx_json", data)
        raw_delivered = meta.get("delivered_amount", tx.get("Amount", 0))
        delivered_amount = int(raw_delivered) if isinstance(raw_delivered, (int, str)) and str(raw_delivered).isdigit() else 0
        destination = tx.get("Destination")
        
        return destination == destination_target and delivered_amount >= required_drops
    except Exception as e:
        logger.error(f"XRPL Verification Error: {e}")
        return False
