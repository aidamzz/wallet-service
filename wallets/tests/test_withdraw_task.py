import pytest
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from wallets.models import Wallet, Transaction
from wallets.tasks import process_withdrawals

@pytest.mark.django_db(transaction=True)
@patch("wallets.tasks.request_third_party_deposit")
def test_withdraw_success_marks_success_and_deducts_balance(mock_bank):
    mock_bank.return_value = {"status": 200}

    w = Wallet.objects.create(balance=1000)
    tx = Transaction.objects.create(
        wallet=w,
        type=Transaction.WITHDRAW,
        status=Transaction.PENDING,
        amount=200,
        execute_at=timezone.now() - timedelta(seconds=1),  # due now
    )

    # call the task function directly
    process_withdrawals()

    tx.refresh_from_db()
    w.refresh_from_db()

    assert tx.status == Transaction.SUCCESS
    assert w.balance == 800
    assert mock_bank.called
    # confirm it used tx.idempotency_key
    _, kwargs = mock_bank.call_args
    assert kwargs["amount"] == 200
    assert str(kwargs["idempotency_key"]) == str(tx.idempotency_key)

@pytest.mark.django_db(transaction=True)
@patch("wallets.tasks.request_third_party_deposit")
def test_withdraw_insufficient_funds_fails_without_calling_bank(mock_bank):
    mock_bank.return_value = {"status": 200}

    w = Wallet.objects.create(balance=100)
    tx = Transaction.objects.create(
        wallet=w,
        type=Transaction.WITHDRAW,
        status=Transaction.PENDING,
        amount=200,
        execute_at=timezone.now(),
    )

    process_withdrawals()

    tx.refresh_from_db()
    w.refresh_from_db()

    assert tx.status == Transaction.FAILED
    assert w.balance == 100
    assert mock_bank.called is False
