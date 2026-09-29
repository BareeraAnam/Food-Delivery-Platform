import uuid
import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Custom user model shared by every role in the platform. Role determines
    which extra profile (RestaurantOwnerProfile, DriverProfile, ...) applies
    and which DRF permission classes accept the user.
    """

    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        RESTAURANT_OWNER = 'restaurant_owner', 'Restaurant Owner'
        DRIVER = 'driver', 'Driver'
        ADMIN = 'admin', 'Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone_regex = RegexValidator(
        regex=r'^\+?[0-9]{9,15}$',
        message="Phone number must be entered in the format: '+999999999'."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, unique=True, null=True)
    is_phone_verified = models.BooleanField(default=False)

    # Referral system
    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self._generate_unique_referral_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_unique_referral_code():
        while True:
            code = secrets.token_hex(4).upper()  # e.g. "A1B2C3D4"
            if not User.objects.filter(referral_code=code).exists():
                return code

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.role})'


class RestaurantOwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='restaurant_owner_profile')
    business_registration_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f'Owner profile: {self.user}'


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    default_address = models.TextField(blank=True)
    default_latitude = models.FloatField(null=True, blank=True)
    default_longitude = models.FloatField(null=True, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'Customer profile: {self.user}'


class DeviceToken(models.Model):
    """FCM device token for push notifications. A user may have several
    (multiple devices logged in)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(
        max_length=10,
        choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')],
        default='android',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.platform}'
