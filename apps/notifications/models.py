from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class NotificationLog(TimeStampedModel):
    """Audit trail of every push notification attempt, useful for
    debugging delivery issues and for an in-app notification inbox."""
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=500)
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    error_message = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
