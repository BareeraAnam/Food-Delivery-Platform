from django.urls import path
from .views import ReviewCreateView, RestaurantReviewListView, DriverReviewListView

urlpatterns = [
    path('', ReviewCreateView.as_view(), name='review-create'),
    path('restaurant/<uuid:restaurant_id>/', RestaurantReviewListView.as_view(), name='restaurant-reviews'),
    path('driver/<uuid:driver_id>/', DriverReviewListView.as_view(), name='driver-reviews'),
]
