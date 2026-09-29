from django.urls import re_path
from .consumers import OrderTrackingConsumer, DriverFleetConsumer

websocket_urlpatterns = [
    re_path(r'^ws/orders/(?P<order_id>[0-9a-f-]+)/$', OrderTrackingConsumer.as_asgi()),
    re_path(r'^ws/fleet/$', DriverFleetConsumer.as_asgi()),
]
