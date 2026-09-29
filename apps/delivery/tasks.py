from celery import shared_task
from datetime import timedelta
from django.utils import timezone


@shared_task
def cleanup_stale_driver_locations():
    """
    Celery Beat task (every 30 min): if a driver hasn't sent a GPS ping in
    over 20 minutes, assume their app was closed and mark them unavailable
    so they stop being matched to new orders.
    """
    from .models import DriverProfile

    stale_cutoff = timezone.now() - timedelta(minutes=20)
    updated = DriverProfile.objects.filter(
        is_available=True, last_location_update__lt=stale_cutoff
    ).update(is_available=False)
    return f'{updated} stale driver(s) marked unavailable'
