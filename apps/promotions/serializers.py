from decimal import Decimal

from rest_framework import serializers
from .models import PromoCode, ReferralReward


class PromoCodeSerializer(serializers.ModelSerializer):
    times_used = serializers.IntegerField(read_only=True)

    class Meta:
        model = PromoCode
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'max_discount_amount', 'minimum_order_amount', 'valid_from',
            'valid_until', 'usage_limit_total', 'usage_limit_per_user',
            'is_active', 'restaurant', 'times_used',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        valid_from = attrs.get('valid_from', getattr(self.instance, 'valid_from', None))
        valid_until = attrs.get('valid_until', getattr(self.instance, 'valid_until', None))
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError('valid_until must be after valid_from.')

        discount_type = attrs.get('discount_type', getattr(self.instance, 'discount_type', None))
        discount_value = attrs.get('discount_value', getattr(self.instance, 'discount_value', None))
        if discount_type == PromoCode.DiscountType.PERCENTAGE and discount_value and discount_value > 100:
            raise serializers.ValidationError({'discount_value': 'Percentage discount cannot exceed 100.'})
        return attrs


class PromoCodeValidateSerializer(serializers.Serializer):
    """Lightweight endpoint used by the cart screen to preview a discount
    before the user actually checks out."""
    code = serializers.CharField()
    order_subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))


class ReferralRewardSerializer(serializers.ModelSerializer):
    referred_user_name = serializers.CharField(source='referred_user.get_full_name', read_only=True)

    class Meta:
        model = ReferralReward
        fields = ['id', 'referred_user_name', 'reward_amount', 'status', 'granted_at', 'created_at']
