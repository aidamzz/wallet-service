from django.urls import path
from wallets.views import CreateWalletView, RetrieveWalletView, CreateDepositView, ScheduleWithdrawView, RetrieveTransactionView

urlpatterns = [
    path("", CreateWalletView.as_view(), name="create-wallet"),
    path("<uuid:uuid>/", RetrieveWalletView.as_view(), name="retrieve-wallet"),
    path("deposit/", CreateDepositView.as_view(), name="deposit"),
    path("withdraw/", ScheduleWithdrawView.as_view(), name="withdraw"),
    path("transactions/<uuid:id>/", RetrieveTransactionView.as_view()),
]
