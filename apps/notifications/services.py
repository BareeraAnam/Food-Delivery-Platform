"""
Thin wrapper around firebase-admin so the rest of the codebase never talks
to the FCM SDK directly — makes it trivial to swap providers later or mock
in tests.
"""
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    """Lazily initializes the Firebase Admin app exactly once per process."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    import firebase_admin
    from firebase_admin import credentials

    cred_path = settings.FCM_CREDENTIALS_FILE
    if not os.path.exists(cred_path):
        logger.warning(
            'FCM credentials file "%s" not found — push notifications will be '
            'logged locally instead of sent. See README for setup.', cred_path
        )
        return None

    cred = credentials.Certificate(cred_path)
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_fcm_push(*, tokens, title, body, data=None):
    """
    Sends a push notification to one or more device tokens.
    Returns (success_count, failure_count).

    If FCM isn't configured (no credentials file — e.g. local dev), this
    degrades gracefully to a log line instead of raising, so the rest of
    the order flow is never blocked by a missing FCM setup.
    """
    if not tokens:
        return 0, 0

    app = _get_firebase_app()
    if app is None:
        logger.info('[FCM-disabled] Would send "%s" to %d device(s): %s', title, len(tokens), body)
        return 0, 0

    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=list(tokens),
    )
    response = messaging.send_multicast(message)
    return response.success_count, response.failure_count
