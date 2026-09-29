"""
Recalculates the restaurant's / driver's average_rating whenever a review
is created. Kept as a signal (rather than inline in the view) so any future
review-creation path (admin, bulk import, etc.) stays consistent.
"""
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Review


@receiver(post_save, sender=Review)
def update_average_ratings(sender, instance, created, **kwargs):
    if not created:
        return

    restaurant = instance.restaurant
    avg = restaurant.reviews.aggregate(avg=Avg('restaurant_rating'))['avg'] or 0
    restaurant.average_rating = round(avg, 2)
    restaurant.total_reviews = restaurant.reviews.count()
    restaurant.save(update_fields=['average_rating', 'total_reviews'])

    if instance.driver_id and instance.driver_rating:
        driver = instance.driver
        driver_avg = driver.reviews.aggregate(avg=Avg('driver_rating'))['avg'] or 0
        driver.average_rating = round(driver_avg, 2)
        driver.save(update_fields=['average_rating'])
