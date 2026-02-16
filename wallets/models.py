import uuid

from django.db import models
from django.db import transaction
from django.utils import timezone
class Wallet(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    balance = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def deposit(self, amount: int):

        if amount <= 0:
            raise ValueError("Amount must be positive")

        with transaction.atomic():
            wallet = (
                Wallet.objects
                .select_for_update()
                .get(pk=self.pk)
            )

            wallet.balance += amount
            wallet.save(update_fields=["balance"])


class Transaction(models.Model):

    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"

    TYPE_CHOICES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAW, "Withdraw"),
    ]

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    amount = models.BigIntegerField()

    execute_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    retry_count = models.PositiveSmallIntegerField(default=0)
    is_dead = models.BooleanField(default=False)

    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True
    )