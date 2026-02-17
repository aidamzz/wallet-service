from rest_framework import serializers

from wallets.models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("uuid", "balance")
        read_only_fields = ("uuid", "balance")
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            "id", "wallet", "type", "status", "amount",
            "execute_at", "retry_count", "is_dead",
            "created_at", "updated_at",
        )
        read_only_fields = fields