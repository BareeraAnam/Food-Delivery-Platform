from rest_framework import generics, permissions

from apps.common.permissions import IsCustomer

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]


class RestaurantReviewListView(generics.ListAPIView):
    """GET /api/v1/reviews/restaurant/<restaurant_id>/"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Review.objects.filter(restaurant_id=self.kwargs['restaurant_id'])


class DriverReviewListView(generics.ListAPIView):
    """GET /api/v1/reviews/driver/<driver_id>/"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Review.objects.filter(driver_id=self.kwargs['driver_id'])
