from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsDriver
from apps.orders.models import Order

from .models import DriverProfile
from .serializers import DriverProfileSerializer, AvailabilityToggleSerializer, LocationPingSerializer
from .services import record_location_ping


class MyDriverProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = DriverProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def get_object(self):
        profile, _ = DriverProfile.objects.get_or_create(user=self.request.user)
        return profile


class ToggleAvailabilityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request):
        serializer = AvailabilityToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile, _ = DriverProfile.objects.get_or_create(user=request.user)
        profile.is_available = serializer.validated_data['is_available']
        profile.save(update_fields=['is_available'])
        return Response(DriverProfileSerializer(profile).data)


class LocationPingView(APIView):
    """POST /api/v1/delivery/location-ping/ — REST fallback GPS update."""
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request):
        serializer = LocationPingSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        driver = get_object_or_404(DriverProfile, user=request.user)
        order = None
        if data.get('order_id'):
            order = get_object_or_404(Order, pk=data['order_id'])

        record_location_ping(
            driver=driver,
            latitude=data['latitude'],
            longitude=data['longitude'],
            order=order,
            heading=data.get('heading'),
            speed_kmh=data.get('speed_kmh'),
        )
        return Response({'detail': 'Location updated.'}, status=status.HTTP_200_OK)
