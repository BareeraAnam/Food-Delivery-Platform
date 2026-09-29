from rest_framework import serializers

from apps.orders.models import Order
from .models import DriverProfile, DriverLocationPing


class DriverProfileSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = DriverProfile
        fields = [
            'id', 'driver_name', 'vehicle_type', 'license_plate', 'is_verified',
            'is_available', 'current_latitude', 'current_longitude',
            'last_location_update', 'average_rating', 'total_deliveries',
        ]
        read_only_fields = ['id', 'is_verified', 'average_rating', 'total_deliveries', 'last_location_update']


class AvailabilityToggleSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class LocationPingSerializer(serializers.Serializer):
    """
    REST fallback for GPS pings (e.g. background updates when the WebSocket
    connection has dropped). The primary live-tracking path is the
    WebSocket consumer in apps.tracking, which calls the same service.
    """
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    order_id = serializers.UUIDField(required=False)
    heading = serializers.FloatField(required=False, min_value=0, max_value=360)
    speed_kmh = serializers.FloatField(required=False, min_value=0)

    def validate_order_id(self, value):
        if value and not Order.objects.filter(
            pk=value, driver__user=self.context['request'].user
        ).exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).exists():
            raise serializers.ValidationError('This order is not an active delivery assigned to you.')
        return value
