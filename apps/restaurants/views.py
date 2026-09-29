from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.permissions import IsRestaurantOwner, IsOwnerOrReadOnly
from apps.common.geo import haversine_distance_km, bounding_box

from .models import Restaurant, MenuCategory, MenuItem
from .serializers import (
    RestaurantListSerializer, RestaurantDetailSerializer,
    MenuCategorySerializer, MenuItemSerializer,
)


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'cuisine_types']
    ordering_fields = ['average_rating', 'delivery_fee', 'avg_preparation_time_minutes']
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ('create',):
            return [permissions.IsAuthenticated(), IsRestaurantOwner()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'nearby':
            return RestaurantListSerializer
        return RestaurantDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            # Public listing only shows open restaurants unless the owner
            # is viewing their own dashboard via ?mine=true
            if self.request.query_params.get('mine') == 'true' and self.request.user.is_authenticated:
                return qs.filter(owner=self.request.user)
            return qs.filter(status=Restaurant.Status.OPEN)
        return qs

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        GET /api/v1/restaurants/nearby/?lat=..&lon=..&radius_km=8
        Cheap bounding-box DB filter, then precise Haversine sort in Python.
        """
        try:
            lat = float(request.query_params['lat'])
            lon = float(request.query_params['lon'])
        except (KeyError, ValueError):
            return Response(
                {'detail': 'lat and lon query params are required and must be numeric.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        radius_km = float(request.query_params.get('radius_km', 8))

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)
        candidates = Restaurant.objects.filter(
            status=Restaurant.Status.OPEN,
            latitude__range=(min_lat, max_lat),
            longitude__range=(min_lon, max_lon),
        )

        results = []
        for restaurant in candidates:
            distance = haversine_distance_km(lat, lon, restaurant.latitude, restaurant.longitude)
            if distance <= radius_km:
                restaurant.distance_km = round(distance, 2)
                results.append(restaurant)
        results.sort(key=lambda r: r.distance_km)

        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)


class MenuCategoryViewSet(viewsets.ModelViewSet):
    """Nested under /restaurants/<restaurant_slug>/categories/ (see urls.py)."""
    serializer_class = MenuCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsRestaurantOwner]

    def get_queryset(self):
        return MenuCategory.objects.filter(restaurant__slug=self.kwargs['restaurant_slug'])

    def perform_create(self, serializer):
        restaurant = get_object_or_404(
            Restaurant, slug=self.kwargs['restaurant_slug'], owner=self.request.user
        )
        serializer.save(restaurant=restaurant)


class MenuItemViewSet(viewsets.ModelViewSet):
    """Nested under /restaurants/<restaurant_slug>/menu-items/ (see urls.py)."""
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsRestaurantOwner()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return MenuItem.objects.filter(restaurant__slug=self.kwargs['restaurant_slug'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['restaurant'] = get_object_or_404(Restaurant, slug=self.kwargs['restaurant_slug'])
        return context

    def perform_create(self, serializer):
        restaurant = get_object_or_404(
            Restaurant, slug=self.kwargs['restaurant_slug'], owner=self.request.user
        )
        serializer.save(restaurant=restaurant)
