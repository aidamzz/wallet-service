import requests
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from wallets.models import Transaction, Wallet
from wallets.utils import request_third_party_deposit
MAX_RETRIES = 5


def mark_dead(tx: Transaction):
    tx.is_dead = True
    tx.status = Transaction.FAILED
    tx.save(update_fields=["is_dead", "status", "updated_at"])


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True
)
def process_withdrawals(self):
    now = timezone.now()

    due_ids = list(
        Transaction.objects.filter(
            type=Transaction.WITHDRAW,
            status__in=[Transaction.PENDING, Transaction.PROCESSING],
            execute_at__lte=now,
            is_dead=False,
        ).values_list("id", flat=True)
    )

    for tx_id in due_ids:
        # Step 1: under lock:
        # - if PENDING: validate and RESERVE (deduct) funds, then set PROCESSING
        # - if already PROCESSING: funds were already reserved; just continue to bank call
        try:
            with transaction.atomic():
                tx = (
                    Transaction.objects
                    .select_for_update()
                    .get(id=tx_id)
                )

                if tx.is_dead or tx.status not in [Transaction.PENDING, Transaction.PROCESSING]:
                    continue

                wallet = (
                    Wallet.objects
                    .select_for_update()
                    .get(id=tx.wallet_id)
                )

                if tx.status == Transaction.PENDING:
                    # validate at execution time
                    if wallet.balance < tx.amount:
                        tx.status = Transaction.FAILED
                        tx.save(update_fields=["status", "updated_at"])
                        continue

                    # RESERVE funds now (prevents concurrent overspend)
                    wallet.balance -= tx.amount
                    wallet.save(update_fields=["balance"])

                    tx.status = Transaction.PROCESSING
                    tx.save(update_fields=["status", "updated_at"])

            # Step 2: call bank OUTSIDE DB transaction
            payload = request_third_party_deposit(
                amount=tx.amount,
                idempotency_key=tx.idempotency_key,
            )

            if payload.get("status") not in (200):
                raise Exception("Bank failed")

            # Step 3: finalize success under lock
            with transaction.atomic():
                tx = Transaction.objects.select_for_update().get(id=tx_id)

                # someone changed it (shouldn't happen, but safe)
                if tx.status != Transaction.PROCESSING or tx.is_dead:
                    continue

                tx.status = Transaction.SUCCESS
                tx.save(update_fields=["status", "updated_at"])

        except requests.exceptions.RequestException as exc:
            
            with transaction.atomic():
                tx = Transaction.objects.select_for_update().get(id=tx_id)
                if tx.status == Transaction.PROCESSING and not tx.is_dead:
                    tx.retry_count += 1
                    if tx.retry_count >= MAX_RETRIES:
                        # refund reserved funds if we’re giving up
                        wallet = Wallet.objects.select_for_update().get(id=tx.wallet_id)
                        wallet.balance += tx.amount
                        wallet.save(update_fields=["balance"])
                        mark_dead(tx)
                        continue
                    tx.save(update_fields=["retry_count", "updated_at"])
            raise self.retry(exc=exc)

        except Exception as exc:
            with transaction.atomic():
                tx = Transaction.objects.select_for_update().get(id=tx_id)

                if tx.status == Transaction.PROCESSING and not tx.is_dead:
                    tx.retry_count += 1

                    if tx.retry_count >= MAX_RETRIES:
                        # refund 
                        wallet = Wallet.objects.select_for_update().get(id=tx.wallet_id)
                        wallet.balance += tx.amount
                        wallet.save(update_fields=["balance"])

                        mark_dead(tx)
                        continue

                    tx.save(update_fields=["retry_count", "updated_at"])

            raise self.retry(exc=exc)

