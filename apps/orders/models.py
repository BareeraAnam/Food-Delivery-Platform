from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.restaurants.models import Restaurant, MenuItem


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PLACED = 'placed', 'Placed'
        CONFIRMED = 'confirmed', 'Confirmed by Restaurant'
        PREPARING = 'preparing', 'Preparing'
        READY_FOR_PICKUP = 'ready_for_pickup', 'Ready for Pickup'
        PICKED_UP = 'picked_up', 'Picked Up'
        ON_THE_WAY = 'on_the_way', 'On the Way'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    # A status machine: which transitions are legal from a given state.
    # Enforced in serializers/services, not just documentation.
    VALID_TRANSITIONS = {
        Status.PLACED: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PREPARING, Status.CANCELLED},
        Status.PREPARING: {Status.READY_FOR_PICKUP, Status.CANCELLED},
        Status.READY_FOR_PICKUP: {Status.PICKED_UP, Status.CANCELLED},
        Status.PICKED_UP: {Status.ON_THE_WAY},
        Status.ON_THE_WAY: {Status.DELIVERED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }

    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = 'cod', 'Cash on Delivery'
        CARD = 'card', 'Card'
        WALLET = 'wallet', 'Wallet'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders'
    )
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name='orders')
    driver = models.ForeignKey(
        'delivery.DriverProfile', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='deliveries'
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)

    delivery_address = models.TextField()
    delivery_latitude = models.FloatField()
    delivery_longitude = models.FloatField()

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    promo_code = models.ForeignKey(
        'promotions.PromoCode', null=True, blank=True, on_delete=models.SET_NULL, related_name='orders'
    )
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH_ON_DELIVERY)
    is_paid = models.BooleanField(default=False)

    special_instructions = models.TextField(blank=True)

    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f'Order #{str(self.id)[:8]} - {self.status}'

    def can_transition_to(self, new_status):
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    item_name_snapshot = models.CharField(max_length=150)  # preserved even if menu item changes later
    unit_price_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    notes = models.CharField(max_length=255, blank=True)

    @property
    def line_total(self):
        return self.unit_price_snapshot * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.item_name_snapshot}'


class OrderStatusHistory(models.Model):
    """Audit trail; also what the WebSocket consumer broadcasts from."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Order status histories'
