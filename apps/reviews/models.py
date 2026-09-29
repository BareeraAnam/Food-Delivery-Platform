from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class Review(TimeStampedModel):
    """
    A single review left by a customer for a *delivered* order. Rates the
    restaurant and (optionally, if a driver was involved) the driver in one
    submission, since that's how most delivery apps present it to the user.
    """
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_written')

    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='reviews')
    restaurant_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    restaurant_comment = models.TextField(blank=True)

    driver = models.ForeignKey(
        'delivery.DriverProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviews'
    )
    driver_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    driver_comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Review for order #{str(self.order_id)[:8]}'
