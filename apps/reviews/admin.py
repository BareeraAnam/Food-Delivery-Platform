from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'customer', 'restaurant', 'restaurant_rating', 'driver', 'driver_rating', 'created_at')
    list_filter = ('restaurant_rating', 'driver_rating')
