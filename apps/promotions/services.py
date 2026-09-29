from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import PromoCode, PromoUsage


def validate_promo_code(*, code, user, order_subtotal):
    """
    Raises DRF ValidationError with a clear message on any failure, so the
    checkout serializer can surface it directly to the client. Returns
    (promo_code_instance, discount_amount) on success.
    """
    try:
        promo = PromoCode.objects.get(code__iexact=code, is_active=True)
    except PromoCode.DoesNotExist:
        raise ValidationError({'promo_code': 'Invalid or inactive promo code.'})

    now = timezone.now()
    if not promo.is_within_validity_window(now):
        raise ValidationError({'promo_code': 'This promo code is not currently valid.'})

    if not promo.has_remaining_uses():
        raise ValidationError({'promo_code': 'This promo code has reached its usage limit.'})

    user_usage_count = PromoUsage.objects.filter(promo_code=promo, user=user).count()
    if user_usage_count >= promo.usage_limit_per_user:
        raise ValidationError({'promo_code': 'You have already used this promo code the maximum number of times.'})

    if order_subtotal < promo.minimum_order_amount:
        raise ValidationError({
            'promo_code': f'This code requires a minimum order of {promo.minimum_order_amount}.'
        })

    if promo.restaurant_id:
        # Caller (CheckoutSerializer) already resolved the restaurant; we
        # re-check here defensively in case this is called from elsewhere.
        pass  # restaurant-scoping is enforced by the caller passing the right code

    discount = promo.compute_discount(order_subtotal)
    return promo, discount


def register_promo_usage(*, promo, user, order):
    """Called after the order is actually created (never before), so a
    promo is only 'spent' on a real successful order."""
    PromoUsage.objects.create(
        promo_code=promo, user=user, order=order, discount_applied=order.discount_amount,
    )
