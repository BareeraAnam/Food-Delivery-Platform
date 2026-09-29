from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Restaurant(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
        SUSPENDED = 'suspended', 'Suspended'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restaurants'
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)
    cuisine_types = models.CharField(
        max_length=255, help_text='Comma-separated, e.g. "Italian,Fast Food"'
    )
    logo = models.ImageField(upload_to='restaurants/logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='restaurants/banners/', blank=True, null=True)

    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    opening_time = models.TimeField()
    closing_time = models.TimeField()

    avg_preparation_time_minutes = models.PositiveIntegerField(default=20)
    minimum_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-average_rating', 'name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return self.name

    @property
    def cuisine_list(self):
        return [c.strip() for c in self.cuisine_types.split(',') if c.strip()]


class MenuCategory(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ('restaurant', 'name')
        verbose_name_plural = 'Menu categories'

    def __str__(self):
        return f'{self.restaurant.name} - {self.name}'


class MenuItem(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_vegetarian = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    preparation_time_minutes = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['category__display_order', 'name']
        indexes = [models.Index(fields=['restaurant', 'is_available'])]

    def __str__(self):
        return f'{self.name} - {self.restaurant.name}'
