import pytest
from django.utils import timezone
from datetime import timedelta
from wallets.models import Transaction

@pytest.mark.django_db
def test_schedule_withdraw_creates_pending_tx(api_client, wallet):
    future = (timezone.now() + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")

    res = api_client.post(
        "/wallets/withdraw/",
        {"wallet_id": str(wallet.uuid), "amount": 50, "execute_at": future},
        format="json",
    )
    assert res.status_code == 201
    assert "transaction_id" in res.data

    tx_id = res.data["transaction_id"]
    tx = Transaction.objects.get(id=tx_id)
    assert tx.type == Transaction.WITHDRAW
    assert tx.status == Transaction.PENDING
    assert tx.amount == 50

@pytest.mark.django_db
def test_schedule_withdraw_rejects_past_execute_at(api_client, wallet):
    past = (timezone.now() - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    res = api_client.post(
        "/wallets/withdraw/",
        {"wallet_id": str(wallet.uuid), "amount": 50, "execute_at": past},
        format="json",
    )
    assert res.status_code == 400
