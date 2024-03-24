"""Celery task config"""
import os, datetime

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_platform.settings")

app = Celery("news_platform")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "daytime": {
        "task": "news_platform.pageHome.refresh_feeds",
        "schedule": crontab(minute="*/15", hour="5-18"),
        "args": (),
    },
    "nighttime": {
        "task": "news_platform.pageHome.refresh_feeds",
        "schedule": crontab(minute="*/30", hour="18-23"),
        "args": (),
    },
    "afterstartup": {
        "task": "news_platform.pageHome.refresh_feeds",
        "schedule": crontab(
            minute=datetime.datetime.now().minute + 2 if datetime.datetime.now().minute + 2 < 59 else datetime.datetime.now().minute + 2 - 60,
            hour=datetime.datetime.now().hour if datetime.datetime.now().minute + 2 < 59 else datetime.datetime.now().hour + 1,
            day_of_month=datetime.datetime.now().day,
            month_of_year=datetime.datetime.now().month
            ),
        "args": (),
    },
}
