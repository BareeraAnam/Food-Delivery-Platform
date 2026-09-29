from rest_framework import serializers

from apps.orders.models import Order
from .models import Review


class ReviewCreateSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'order_id', 'restaurant_rating', 'restaurant_comment',
            'driver_rating', 'driver_comment', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_order_id(self, value):
        user = self.context['request'].user
        try:
            order = Order.objects.get(pk=value, customer=user)
        except Order.DoesNotExist:
            raise serializers.ValidationError('Order not found.')

        if order.status != Order.Status.DELIVERED:
            raise serializers.ValidationError('You can only review orders that have been delivered.')

        if Review.objects.filter(order=order).exists():
            raise serializers.ValidationError('This order has already been reviewed.')

        self._order = order
        return value

    def validate(self, attrs):
        order = getattr(self, '_order', None)
        # driver_rating only makes sense if the order actually had a driver
        if attrs.get('driver_rating') and order and not order.driver_id:
            raise serializers.ValidationError(
                {'driver_rating': 'This order had no assigned driver to rate.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('order_id')
        order = self._order
        review = Review.objects.create(
            order=order,
            customer=order.customer,
            restaurant=order.restaurant,
            driver=order.driver,
            **validated_data,
        )
        return review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'customer_name', 'restaurant_rating', 'restaurant_comment',
            'driver_rating', 'driver_comment', 'created_at',
        ]
