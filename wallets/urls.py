from django.urls import path

from wallets.views import CreateDepositView, ScheduleWithdrawView, CreateWalletView, RetrieveWalletView

urlpatterns = [
    path("", CreateWalletView.as_view()),
    path("<uuid:uuid>/", RetrieveWalletView.as_view()),
    path("deposit/", CreateDepositView.as_view()),
    path("withdraw/", ScheduleWithdrawView.as_view()),
]
