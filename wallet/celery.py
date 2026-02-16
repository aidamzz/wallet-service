import os
from datetime import timedelta
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wallet.settings")

app = Celery("wallet")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "process-withdrawals-every-5-seconds": {
        "task": "wallets.tasks.process_withdrawals",
        "schedule": timedelta(seconds=5),
    },
}

app.conf.timezone = "UTC"
