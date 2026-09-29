from django.utils.text import slugify
from rest_framework import serializers

from .models import Restaurant, MenuCategory, MenuItem


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            'id', 'category', 'name', 'description', 'image', 'price',
            'is_vegetarian', 'is_available', 'calories', 'preparation_time_minutes',
        ]
        read_only_fields = ['id']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than zero.')
        return value

    def validate_category(self, category):
        """Cross-field-ish validation: category must belong to the same
        restaurant the item is being created for (restaurant comes from the
        URL, injected into serializer context by the view)."""
        restaurant = self.context.get('restaurant')
        if restaurant and category.restaurant_id != restaurant.id:
            raise serializers.ValidationError('This category does not belong to the selected restaurant.')
        return category


class MenuCategorySerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = MenuCategory
        fields = ['id', 'name', 'display_order', 'items']
        read_only_fields = ['id']


class RestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/search endpoints."""
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'slug', 'logo', 'cuisine_types', 'status',
            'average_rating', 'total_reviews', 'delivery_fee',
            'avg_preparation_time_minutes', 'distance_km',
        ]


class RestaurantDetailSerializer(serializers.ModelSerializer):
    categories = MenuCategorySerializer(many=True, read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'owner', 'name', 'slug', 'description', 'cuisine_types',
            'logo', 'banner', 'address', 'latitude', 'longitude', 'status',
            'opening_time', 'closing_time', 'avg_preparation_time_minutes',
            'minimum_order_amount', 'delivery_fee', 'average_rating',
            'total_reviews', 'categories',
        ]
        read_only_fields = ['id', 'owner', 'average_rating', 'total_reviews', 'slug']

    def validate(self, attrs):
        opening = attrs.get('opening_time', getattr(self.instance, 'opening_time', None))
        closing = attrs.get('closing_time', getattr(self.instance, 'closing_time', None))
        if opening and closing and opening >= closing:
            raise serializers.ValidationError('closing_time must be after opening_time.')
        return attrs

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        base_slug = slugify(validated_data['name'])
        slug = base_slug
        counter = 1
        while Restaurant.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        validated_data['slug'] = slug
        return super().create(validated_data)
