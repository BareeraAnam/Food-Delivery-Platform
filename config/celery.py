import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('food_delivery')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# Celery Beat schedule — periodic tasks (promotions, cleanup, reports)

app.conf.beat_schedule = {
    'deactivate-expired-promo-codes': {
        'task': 'apps.promotions.tasks.deactivate_expired_promo_codes',
        'schedule': crontab(minute=0),  # every hour
    },
    'activate-scheduled-promo-codes': {
        'task': 'apps.promotions.tasks.activate_scheduled_promo_codes',
        'schedule': crontab(minute=0),  # every hour
    },
    'send-daily-promo-digest': {
        'task': 'apps.promotions.tasks.send_daily_promo_digest',
        'schedule': crontab(hour=9, minute=0),  # every day at 09:00
    },
    'cleanup-stale-driver-locations': {
        'task': 'apps.delivery.tasks.cleanup_stale_driver_locations',
        'schedule': crontab(minute='*/30'),  # every 30 minutes
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
