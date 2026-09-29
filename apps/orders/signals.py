"""
Reserved for order-related signals. Referral first-order bonus is handled
here so it stays decoupled from the checkout view/service.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order


@receiver(post_save, sender=Order)
def reward_referrer_on_first_order(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.promotions.tasks import reward_referral_on_first_order
    reward_referral_on_first_order.delay(order_id=str(instance.id))
