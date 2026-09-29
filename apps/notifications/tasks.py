from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push_notification_task(self, *, user_id, title, body, data=None):
    """
    Fire-and-forget push notification, always called via .delay() from
    other apps' services/signals so the HTTP request/response cycle is
    never slowed down by a call to Firebase.
    """
    from apps.accounts.models import User, DeviceToken
    from .models import NotificationLog
    from .services import send_fcm_push

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return f'User {user_id} not found'

    tokens = list(
        DeviceToken.objects.filter(user=user, is_active=True).values_list('token', flat=True)
    )

    try:
        success_count, failure_count = send_fcm_push(tokens=tokens, title=title, body=body, data=data)
        NotificationLog.objects.create(user=user, title=title, body=body, data=data or {}, status=NotificationLog.Status.SENT)
        return f'Sent to {success_count} device(s), {failure_count} failed'
    except Exception as exc:  # pragma: no cover - network/SDK errors
        NotificationLog.objects.create(
            user=user, title=title, body=body, data=data or {},
            status=NotificationLog.Status.FAILED, error_message=str(exc),
        )
        raise self.retry(exc=exc)
