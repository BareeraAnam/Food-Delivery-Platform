from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsRestaurantOwner

from .models import PromoCode, ReferralReward
from .serializers import PromoCodeSerializer, PromoCodeValidateSerializer, ReferralRewardSerializer
from .services import validate_promo_code


class PromoCodeListCreateView(generics.ListCreateAPIView):
    """Restaurant owners manage promo codes for their own restaurant;
    platform-wide codes (restaurant=null) are admin-managed via /admin/."""
    serializer_class = PromoCodeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsRestaurantOwner()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = PromoCode.objects.filter(is_active=True)
        restaurant_id = self.request.query_params.get('restaurant_id')
        if restaurant_id:
            qs = qs.filter(models_q_restaurant(restaurant_id))
        return qs

    def perform_create(self, serializer):
        serializer.save(restaurant_id=self.request.data.get('restaurant'))


def models_q_restaurant(restaurant_id):
    from django.db.models import Q
    return Q(restaurant_id=restaurant_id) | Q(restaurant__isnull=True)


class PromoCodeValidateView(APIView):
    """POST /api/v1/promotions/validate/ — preview a discount before checkout."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PromoCodeValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promo, discount = validate_promo_code(
            code=serializer.validated_data['code'],
            user=request.user,
            order_subtotal=serializer.validated_data['order_subtotal'],
        )
        return Response({
            'valid': True,
            'code': promo.code,
            'discount_amount': discount,
            'final_total': serializer.validated_data['order_subtotal'] - discount,
        })


class MyReferralRewardsView(generics.ListAPIView):
    serializer_class = ReferralRewardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReferralReward.objects.filter(referrer=self.request.user)
