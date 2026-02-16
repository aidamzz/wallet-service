from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from wallets.serializers import WalletSerializer
from django.db import transaction
from rest_framework import status
from wallets.models import Wallet, Transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone

class CreateWalletView(CreateAPIView):
    serializer_class = WalletSerializer


class RetrieveWalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    lookup_field = "uuid"


class CreateDepositView(APIView):

    def post(self, request, *args, **kwargs):

        wallet_id = request.data.get("wallet_id")
        amount = request.data.get("amount")

        if not wallet_id or not amount:
            return Response(
                {"error": "wallet_id and amount required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = int(amount)

        if amount <= 0:
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():

                wallet = (
                    Wallet.objects
                    .select_for_update()
                    .get(uuid=wallet_id)
                )

                wallet.balance += amount
                wallet.save()

                Transaction.objects.create(
                    wallet=wallet,
                    type=Transaction.DEPOSIT,
                    status=Transaction.SUCCESS,
                    amount=amount
                )

        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"balance": wallet.balance},
            status=status.HTTP_200_OK
        )




class ScheduleWithdrawView(APIView):

    def post(self, request, *args, **kwargs):

        wallet_id = request.data.get("wallet_id")
        amount = request.data.get("amount")
        execute_at = request.data.get("execute_at")

        if not all([wallet_id, amount, execute_at]):
            return Response(
                {"error": "Missing fields"},
                status=400
            )

        amount = int(amount)
        
        execute_at = parse_datetime(execute_at)
        if execute_at is None:
            return Response(
                {"error": "Invalid execute_at datetime format. Use ISO 8601 like 2026-02-16T16:10:42Z"},
                status=400
            )
        if execute_at <= timezone.now():
            return Response(
                {"error": "execute_at must be in future"},
                status=400
            )

        try:
            wallet = Wallet.objects.get(uuid=wallet_id)

            tx = Transaction.objects.create(
                wallet=wallet,
                type=Transaction.WITHDRAW,
                amount=amount,
                execute_at=execute_at,
                status=Transaction.PENDING
            )

        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found"},
                status=404
            )

        return Response(
            {"transaction_id": tx.id},
            status=201
        )

