from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet, MenuCategoryViewSet, MenuItemViewSet

router = DefaultRouter()
router.register('', RestaurantViewSet, basename='restaurant')

category_list = MenuCategoryViewSet.as_view({'get': 'list', 'post': 'create'})
category_detail = MenuCategoryViewSet.as_view({
    'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy',
})
menu_item_list = MenuItemViewSet.as_view({'get': 'list', 'post': 'create'})
menu_item_detail = MenuItemViewSet.as_view({
    'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy',
})

urlpatterns = [
    path('<slug:restaurant_slug>/categories/', category_list, name='restaurant-categories-list'),
    path('<slug:restaurant_slug>/categories/<uuid:pk>/', category_detail, name='restaurant-categories-detail'),
    path('<slug:restaurant_slug>/menu-items/', menu_item_list, name='restaurant-menu-items-list'),
    path('<slug:restaurant_slug>/menu-items/<uuid:pk>/', menu_item_detail, name='restaurant-menu-items-detail'),
    path('', include(router.urls)),
]
