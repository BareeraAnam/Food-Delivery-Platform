from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsCustomer, IsRestaurantOwner, IsDriver

from .models import Order
from .serializers import (
    CheckoutSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderStatusUpdateSerializer,
)
from .services import create_order_from_checkout, transition_order_status


class CheckoutView(APIView):
    """POST /api/v1/orders/checkout/ — places a new order."""
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = create_order_from_checkout(user=request.user, validated_data=serializer.validated_data)
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """Returns orders scoped to the requester's role."""
    serializer_class = OrderListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Order.objects.filter(customer=user)
        if user.role == 'restaurant_owner':
            return Order.objects.filter(restaurant__owner=user)
        if user.role == 'driver':
            return Order.objects.filter(driver__user=user)
        return Order.objects.all()  # admin


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.role == 'customer':
            return qs.filter(customer=user)
        if user.role == 'restaurant_owner':
            return qs.filter(restaurant__owner=user)
        if user.role == 'driver':
            return qs.filter(driver__user=user)
        return qs


class OrderStatusUpdateView(APIView):
    """
    PATCH /api/v1/orders/<id>/status/
    Restaurant owners move: placed -> confirmed -> preparing -> ready_for_pickup
    Drivers move: ready_for_pickup -> picked_up -> on_the_way -> delivered
    Either party (or customer, within the allowed window) can cancel.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        self._check_role_permission(request, order)

        serializer = OrderStatusUpdateSerializer(data=request.data, context={'order': order})
        serializer.is_valid(raise_exception=True)

        updated = transition_order_status(
            order=order,
            new_status=serializer.validated_data['status'],
            changed_by=request.user,
            note=serializer.validated_data.get('note', ''),
        )
        return Response(OrderDetailSerializer(updated).data)

    @staticmethod
    def _check_role_permission(request, order):
        user = request.user
        allowed = (
            (user.role == 'restaurant_owner' and order.restaurant.owner_id == user.id)
            or (user.role == 'driver' and order.driver and order.driver.user_id == user.id)
            or (user.role == 'customer' and order.customer_id == user.id)
            or user.is_staff
        )
        if not allowed:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to update this order.')
