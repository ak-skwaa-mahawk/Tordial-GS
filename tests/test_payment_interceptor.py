import pytest
from unittest.mock import MagicMock, patch
from core.mesh.payment_interceptor import verify_xrpl_payment

def test_verify_xrpl_payment_unconfigured_wallet():
    # Must reject if default placeholder wallet is present
    assert verify_xrpl_payment("SOME_HASH", 500, target_wallet="rYourRealWalletAddressHere") is False

@patch("core.mesh.payment_interceptor.client.request")
def test_verify_xrpl_payment_success(mock_request):
    mock_res = MagicMock()
    mock_res.is_successful.return_value = True
    mock_res.result = {
        "validated": True,
        "meta": {
            "TransactionResult": "tesSUCCESS",
            "delivered_amount": "500"
        },
        "Destination": "rProductionWallet123456789"
    }
    mock_request.return_value = mock_res
    
    is_valid = verify_xrpl_payment("TX_HASH_VALID", 500, target_wallet="rProductionWallet123456789")
    assert is_valid is True

@patch("core.mesh.payment_interceptor.client.request")
def test_verify_xrpl_payment_underpaid(mock_request):
    mock_res = MagicMock()
    mock_res.is_successful.return_value = True
    mock_res.result = {
        "validated": True,
        "meta": {
            "TransactionResult": "tesSUCCESS",
            "delivered_amount": "200"
        },
        "Destination": "rProductionWallet123456789"
    }
    mock_request.return_value = mock_res
    
    is_valid = verify_xrpl_payment("TX_HASH_UNDERPAID", 500, target_wallet="rProductionWallet123456789")
    assert is_valid is False
