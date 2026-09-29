"""
Reserved for account-related signals (e.g. welcome email/notification on
user creation). Kept separate from models.py to avoid import-order issues
and circular imports with the notifications app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def send_welcome_notification(sender, instance, created, **kwargs):
    if not created:
        return
    # Imported lazily to avoid a hard dependency loop at app-loading time.
    from apps.notifications.tasks import send_push_notification_task
    send_push_notification_task.delay(
        user_id=str(instance.id),
        title='Welcome to FoodDash! 🎉',
        body='Your account has been created successfully.',
        data={'type': 'welcome'},
    )
