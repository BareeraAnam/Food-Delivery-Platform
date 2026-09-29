from decimal import Decimal

from rest_framework import serializers

from apps.restaurants.models import Restaurant, MenuItem
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInputSerializer(serializers.Serializer):
    """Not a ModelSerializer: used only to validate the raw checkout payload
    before we build real OrderItem rows with price snapshots."""
    menu_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=50)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'item_name_snapshot', 'unit_price_snapshot', 'quantity', 'notes', 'line_total']
        read_only_fields = fields


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ['status', 'note', 'created_at']


class CheckoutSerializer(serializers.Serializer):
    """
    Complex validation example:
      - restaurant must exist and be open
      - every menu item must belong to that restaurant AND be available
      - order subtotal must meet the restaurant's minimum_order_amount
      - optional promo code is validated against the promotions app
    This mirrors a real "place order" endpoint used by the mobile app.
    """
    restaurant_id = serializers.UUIDField()
    items = OrderItemInputSerializer(many=True, min_length=1)
    delivery_address = serializers.CharField()
    delivery_latitude = serializers.FloatField()
    delivery_longitude = serializers.FloatField()
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    promo_code = serializers.CharField(required=False, allow_blank=True)
    special_instructions = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_restaurant_id(self, value):
        try:
            restaurant = Restaurant.objects.get(pk=value)
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError('Restaurant not found.')
        if restaurant.status != Restaurant.Status.OPEN:
            raise serializers.ValidationError('This restaurant is not currently accepting orders.')
        self._restaurant = restaurant
        return value

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('Order must contain at least one item.')
        # Detect duplicate menu_item_id entries early (should be merged client-side)
        ids = [item['menu_item_id'] for item in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Duplicate menu items in cart — merge quantities instead.')
        return items

    def validate(self, attrs):
        restaurant = getattr(self, '_restaurant', None) or Restaurant.objects.filter(
            pk=attrs['restaurant_id']
        ).first()
        if restaurant is None:
            raise serializers.ValidationError({'restaurant_id': 'Restaurant not found.'})

        menu_item_ids = [i['menu_item_id'] for i in attrs['items']]
        menu_items = {
            str(mi.id): mi for mi in MenuItem.objects.filter(id__in=menu_item_ids, restaurant=restaurant)
        }

        subtotal = Decimal('0.00')
        resolved_items = []
        for entry in attrs['items']:
            menu_item = menu_items.get(str(entry['menu_item_id']))
            if menu_item is None:
                raise serializers.ValidationError(
                    {'items': f"Menu item {entry['menu_item_id']} does not belong to this restaurant."}
                )
            if not menu_item.is_available:
                raise serializers.ValidationError(
                    {'items': f'"{menu_item.name}" is currently unavailable.'}
                )
            line_total = menu_item.price * entry['quantity']
            subtotal += line_total
            resolved_items.append({'menu_item': menu_item, 'quantity': entry['quantity'], 'notes': entry.get('notes', '')})

        if subtotal < restaurant.minimum_order_amount:
            raise serializers.ValidationError(
                {'items': f'Minimum order amount for this restaurant is {restaurant.minimum_order_amount}.'}
            )

        attrs['_restaurant'] = restaurant
        attrs['_resolved_items'] = resolved_items
        attrs['_subtotal'] = subtotal

        # Promo code validation delegated to the promotions app so the two
        # domains stay decoupled (orders doesn't own discount rules).
        promo_code_str = attrs.get('promo_code')
        if promo_code_str:
            from apps.promotions.services import validate_promo_code
            promo, discount = validate_promo_code(
                code=promo_code_str,
                user=self.context['request'].user,
                order_subtotal=subtotal,
            )
            attrs['_promo'] = promo
            attrs['_discount'] = discount
        else:
            attrs['_promo'] = None
            attrs['_discount'] = Decimal('0.00')

        return attrs


class OrderListSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'restaurant_name', 'status', 'total_amount', 'created_at', 'estimated_delivery_time',
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'restaurant', 'restaurant_name', 'driver', 'driver_name',
            'status', 'delivery_address', 'delivery_latitude', 'delivery_longitude',
            'subtotal', 'delivery_fee', 'discount_amount', 'total_amount',
            'payment_method', 'is_paid', 'special_instructions',
            'estimated_delivery_time', 'delivered_at', 'cancelled_reason',
            'items', 'status_history', 'created_at',
        ]
        read_only_fields = [f for f in fields if f not in ('special_instructions',)]

    def get_driver_name(self, obj):
        return obj.driver.user.get_full_name() if obj.driver else None


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_status(self, value):
        order = self.context['order']
        if not order.can_transition_to(value):
            raise serializers.ValidationError(
                f'Cannot transition order from "{order.status}" to "{value}".'
            )
        return value
