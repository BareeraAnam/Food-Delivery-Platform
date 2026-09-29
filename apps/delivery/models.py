from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class DriverProfile(TimeStampedModel):
    class VehicleType(models.TextChoices):
        BIKE = 'bike', 'Bike'
        MOTORCYCLE = 'motorcycle', 'Motorcycle'
        CAR = 'car', 'Car'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_profile')
    vehicle_type = models.CharField(max_length=15, choices=VehicleType.choices, default=VehicleType.MOTORCYCLE)
    license_plate = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=False, help_text='Toggled on/off by the driver from the app.')

    # Latest known position, denormalized for fast "nearest driver" queries.
    # The full history lives in DriverLocationPing.
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_deliveries = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['current_latitude', 'current_longitude']),
        ]

    def __str__(self):
        return f'Driver: {self.user}'


class DriverLocationPing(models.Model):
    """
    Append-only GPS trail. The mobile app sends one of these every few
    seconds while a driver has an active delivery; the WebSocket consumer
    also writes here so history survives reconnects/restarts.
    """
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='location_pings')
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL, related_name='driver_pings')
    latitude = models.FloatField()
    longitude = models.FloatField()
    heading = models.FloatField(null=True, blank=True, help_text='Compass heading in degrees, 0-360.')
    speed_kmh = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [models.Index(fields=['driver', 'recorded_at'])]
