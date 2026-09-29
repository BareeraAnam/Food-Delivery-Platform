from celery import shared_task
from django.utils import timezone


@shared_task
def deactivate_expired_promo_codes():
    """Celery Beat: runs hourly. Auto-disables codes past their valid_until."""
    from .models import PromoCode
    now = timezone.now()
    updated = PromoCode.objects.filter(is_active=True, valid_until__lt=now).update(is_active=False)
    return f'{updated} promo code(s) deactivated'


@shared_task
def activate_scheduled_promo_codes():
    """Celery Beat: runs hourly. Auto-enables codes whose valid_from has
    just started (for promos created ahead of time and scheduled)."""
    from .models import PromoCode
    now = timezone.now()
    updated = PromoCode.objects.filter(
        is_active=False, valid_from__lte=now, valid_until__gte=now
    ).update(is_active=True)
    return f'{updated} promo code(s) activated'


@shared_task
def send_daily_promo_digest():
    """Celery Beat: runs daily at 09:00. Pushes active promos to customers
    who have opted into marketing notifications."""
    from apps.accounts.models import User
    from apps.notifications.tasks import send_push_notification_task
    from .models import PromoCode

    now = timezone.now()
    active_promos = PromoCode.objects.filter(is_active=True, valid_from__lte=now, valid_until__gte=now)
    if not active_promos.exists():
        return 'No active promos today'

    headline = active_promos.first()
    customer_ids = User.objects.filter(role=User.Role.CUSTOMER).values_list('id', flat=True)
    for user_id in customer_ids:
        send_push_notification_task.delay(
            user_id=str(user_id),
            title='Today\'s deals are here! 🔥',
            body=f'Use code {headline.code} — {headline.description or "special offer"}.',
            data={'type': 'promo_digest', 'promo_code': headline.code},
        )
    return f'Digest queued for {customer_ids.count()} customers'


@shared_task
def reward_referral_on_first_order(order_id):
    """
    Triggered from apps.orders.signals on every order creation. Grants the
    referrer's reward only the first time the referred user completes an
    order (idempotent via ReferralReward.status).
    """
    from django.conf import settings
    from django.db import transaction
    from apps.orders.models import Order
    from .models import ReferralReward

    try:
        order = Order.objects.select_related('customer', 'customer__referred_by').get(pk=order_id)
    except Order.DoesNotExist:
        return 'Order not found'

    customer = order.customer
    if not customer.referred_by_id:
        return 'Customer was not referred'

    # Only reward on the customer's FIRST ever order
    if Order.objects.filter(customer=customer).count() > 1:
        return 'Not the customer\'s first order'

    with transaction.atomic():
        reward, created = ReferralReward.objects.get_or_create(
            referred_user=customer,
            defaults={
                'referrer': customer.referred_by,
                'reward_amount': settings.REFERRAL_BONUS_AMOUNT,
            },
        )
        if reward.status == ReferralReward.Status.GRANTED:
            return 'Reward already granted'

        # Credit the referrer's wallet
        from apps.accounts.models import CustomerProfile
        profile, _ = CustomerProfile.objects.get_or_create(user=reward.referrer)
        profile.wallet_balance += reward.reward_amount
        profile.save(update_fields=['wallet_balance'])

        reward.status = ReferralReward.Status.GRANTED
        reward.granted_at = timezone.now()
        reward.save(update_fields=['status', 'granted_at'])

    from apps.notifications.tasks import send_push_notification_task
    send_push_notification_task.delay(
        user_id=str(reward.referrer_id),
        title='Referral bonus unlocked! 🎁',
        body=f'You earned {reward.reward_amount} for referring a friend.',
        data={'type': 'referral_reward'},
    )
    return 'Reward granted'
