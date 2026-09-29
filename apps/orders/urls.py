from django.urls import path
from .views import CheckoutView, OrderListView, OrderDetailView, OrderStatusUpdateView

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='order-checkout'),
    path('', OrderListView.as_view(), name='order-list'),
    path('<uuid:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:pk>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
]
