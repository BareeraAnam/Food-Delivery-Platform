from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class PromoCode(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FLAT = 'flat', 'Flat Amount'

    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=255, blank=True)

    discount_type = models.CharField(max_length=12, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    max_discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Caps the discount for percentage codes, e.g. "up to Rs. 200 off".'
    )
    minimum_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    usage_limit_total = models.PositiveIntegerField(
        null=True, blank=True, help_text='Total redemptions allowed across all users. Blank = unlimited.'
    )
    usage_limit_per_user = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', null=True, blank=True, on_delete=models.CASCADE,
        related_name='promo_codes', help_text='Blank = valid platform-wide.'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    @property
    def times_used(self):
        return self.usages.count()

    def is_within_validity_window(self, at):
        return self.valid_from <= at <= self.valid_until

    def has_remaining_uses(self):
        if self.usage_limit_total is None:
            return True
        return self.times_used < self.usage_limit_total

    def compute_discount(self, order_subtotal: Decimal) -> Decimal:
        if self.discount_type == self.DiscountType.FLAT:
            discount = self.discount_value
        else:
            discount = (order_subtotal * self.discount_value) / Decimal('100')
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)
        return min(discount, order_subtotal)


class PromoUsage(models.Model):
    """One row per time a user redeems a promo code — used to enforce
    usage_limit_per_user and usage_limit_total, and for reporting."""
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_usages')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='promo_usage')
    discount_applied = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['promo_code', 'user'])]


class ReferralReward(TimeStampedModel):
    """Tracks a referral bonus so it is granted exactly once, on the
    referred user's first completed order."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending (waiting for first order)'
        GRANTED = 'granted', 'Granted'

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_rewards_earned')
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_reward')
    reward_amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    granted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.referrer} referred {self.referred_user} ({self.status})'
