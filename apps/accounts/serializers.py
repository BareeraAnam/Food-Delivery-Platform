from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, RestaurantOwnerProfile, CustomerProfile, DeviceToken


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles registration for every role. Demonstrates complex/cross-field
    DRF validation:
      - password confirmation match
      - referral code existence check
      - role-specific required fields
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'phone_number',
            'role', 'password', 'password_confirm', 'referral_code',
        ]
        read_only_fields = ['id']

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError('Admin accounts cannot be self-registered.')
        return value

    def validate_referral_code(self, value):
        if value and not User.objects.filter(referral_code=value).exists():
            raise serializers.ValidationError('Invalid referral code.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        password = validated_data.pop('password')

        referred_by = None
        if referral_code:
            referred_by = User.objects.filter(referral_code=referral_code).first()

        user = User(**validated_data, referred_by=referred_by)
        user.set_password(password)
        user.save()

        # Create the matching role profile
        if user.role == User.Role.CUSTOMER:
            CustomerProfile.objects.create(user=user)
        elif user.role == User.Role.RESTAURANT_OWNER:
            RestaurantOwnerProfile.objects.create(user=user)

        # Referral reward is granted asynchronously once the referred user
        # places their first order — see apps.promotions.tasks.reward_referral
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been disabled.')
        attrs['user'] = user
        return attrs

    def to_representation(self, instance):
        user = instance['user']
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'role', 'referral_code', 'is_phone_verified',
        ]
        read_only_fields = ['id', 'role', 'referral_code']


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'platform', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = self.context['request'].user
        token, _created = DeviceToken.objects.update_or_create(
            token=validated_data['token'],
            defaults={'user': user, 'platform': validated_data.get('platform', 'android'), 'is_active': True},
        )
        return token
