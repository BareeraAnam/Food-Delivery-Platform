from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.geo import haversine_distance_km, bounding_box

from .models import DriverProfile


def find_nearest_available_drivers(*, latitude, longitude, radius_km=None, limit=5):
    """
    Two-step search:
      1. Cheap DB bounding-box filter (uses the lat/lon index) to shrink the
         candidate set.
      2. Precise Haversine distance computed in Python, sorted ascending.
    Good enough at moderate scale; swap for PostGIS ST_DWithin if the fleet
    grows large enough that step 2 becomes a bottleneck.
    """
    radius_km = radius_km or settings.DELIVERY_SEARCH_RADIUS_KM
    min_lat, max_lat, min_lon, max_lon = bounding_box(latitude, longitude, radius_km)

    candidates = DriverProfile.objects.filter(
        is_available=True,
        is_verified=True,
        current_latitude__range=(min_lat, max_lat),
        current_longitude__range=(min_lon, max_lon),
    ).select_related('user')

    scored = []
    for driver in candidates:
        distance = haversine_distance_km(latitude, longitude, driver.current_latitude, driver.current_longitude)
        if distance <= radius_km:
            scored.append((distance, driver))

    scored.sort(key=lambda pair: pair[0])
    return [driver for _distance, driver in scored[:limit]]


@transaction.atomic
def assign_nearest_driver(order):
    """
    Called when an order becomes READY_FOR_PICKUP. Finds the nearest
    available driver to the restaurant and assigns them. In production this
    would likely fan out an offer to N nearby drivers and accept the first
    to respond (via a dedicated WebSocket "driver offer" flow); this
    simplified version assigns the single closest driver directly and
    notifies them.
    """
    if order.driver_id:
        return order.driver  # already assigned

    restaurant = order.restaurant
    nearest = find_nearest_available_drivers(
        latitude=restaurant.latitude, longitude=restaurant.longitude, limit=1
    )
    if not nearest:
        return None

    driver = nearest[0]
    driver.is_available = False
    driver.save(update_fields=['is_available'])

    order.driver = driver
    order.save(update_fields=['driver', 'updated_at'])

    from apps.notifications.tasks import send_push_notification_task
    send_push_notification_task.delay(
        user_id=str(driver.user_id),
        title='New delivery assigned 🏍️',
        body=f'Pick up order #{str(order.id)[:8]} from {restaurant.name}.',
        data={'type': 'delivery_assigned', 'order_id': str(order.id)},
    )
    return driver


def record_location_ping(*, driver, latitude, longitude, order=None, heading=None, speed_kmh=None):
    """Persists a GPS ping and updates the driver's denormalized last-known
    position, then broadcasts it over the order's WebSocket group (if any)."""
    from .models import DriverLocationPing

    DriverLocationPing.objects.create(
        driver=driver, order=order, latitude=latitude, longitude=longitude,
        heading=heading, speed_kmh=speed_kmh,
    )
    driver.current_latitude = latitude
    driver.current_longitude = longitude
    driver.last_location_update = timezone.now()
    driver.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])

    if order:
        _broadcast_driver_location(order, latitude, longitude, heading, speed_kmh)


def _broadcast_driver_location(order, latitude, longitude, heading, speed_kmh):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f'order_{order.id}',
        {
            'type': 'driver.location_update',
            'order_id': str(order.id),
            'latitude': latitude,
            'longitude': longitude,
            'heading': heading,
            'speed_kmh': speed_kmh,
        },
    )
