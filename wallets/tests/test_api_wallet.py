import pytest
from wallets.models import Transaction

@pytest.mark.django_db
def test_create_wallet(api_client):
    # urls.py: path("", CreateWalletView.as_view(), name="create-wallet")
    res = api_client.post("/wallets/", {})
    assert res.status_code in (200, 201)
    assert "uuid" in res.data
    assert "balance" in res.data

@pytest.mark.django_db
def test_deposit_increases_balance(api_client, wallet):
    res = api_client.post(
        "/wallets/deposit/",
        {"wallet_id": str(wallet.uuid), "amount": 100},
        format="json",
    )
    assert res.status_code == 200

    wallet.refresh_from_db()
    assert wallet.balance == 100

    # You create a SUCCESS deposit transaction in the view
    assert Transaction.objects.filter(
        wallet=wallet, type=Transaction.DEPOSIT, status=Transaction.SUCCESS, amount=100
    ).exists()

@pytest.mark.django_db
def test_deposit_invalid_amount(api_client, wallet):
    res = api_client.post(
        "/wallets/deposit/",
        {"wallet_id": str(wallet.uuid), "amount": -5},
        format="json",
    )
    assert res.status_code == 400
