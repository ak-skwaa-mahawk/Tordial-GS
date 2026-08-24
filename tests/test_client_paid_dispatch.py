import pytest
from scripts.client_paid_dispatch import TARGET_WALLET, NODE_ENDPOINT

def test_client_dispatch_config():
    assert TARGET_WALLET.startswith("r")
    assert "/api/v1/e8/dispatch" in NODE_ENDPOINT
