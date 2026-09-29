from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async


class OrderTrackingConsumer(AsyncJsonWebsocketConsumer):
    """
    One "room" per order: group name `order_<order_id>`.

    Connect:   ws://host/ws/orders/<order_id>/?token=<jwt>
    Joins:     customer who placed the order, the restaurant owner, and the
               assigned driver — anyone else is rejected in `connect()`.

    Server -> client events (broadcast via order.services / delivery.services):
        {"type": "status_update", "status": "...", "status_display": "...", "updated_at": "..."}
        {"type": "driver_location", "latitude": .., "longitude": .., "heading": .., "speed_kmh": ..}

    Client -> server events (driver app only):
        {"action": "location_update", "latitude": .., "longitude": .., "heading": .., "speed_kmh": ..}
    """

    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.group_name = f'order_{self.order_id}'
        user = self.scope['user']

        if not user or not user.is_authenticated:
            await self.close(code=4001)  # unauthorized
            return

        order = await self._get_order(self.order_id)
        if order is None:
            await self.close(code=4004)  # not found
            return

        if not await self._user_can_access_order(user, order):
            await self.close(code=4003)  # forbidden
            return

        self.order = order
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'order_id': str(order.id), 'status': order.status})

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get('action')
        user = self.scope['user']

        if action == 'location_update':
            if user.role != 'driver':
                await self.send_json({'type': 'error', 'detail': 'Only drivers can send location updates.'})
                return
            await self._handle_location_update(user, content)
        else:
            await self.send_json({'type': 'error', 'detail': f'Unknown action "{action}".'})

    async def _handle_location_update(self, user, content):
        try:
            latitude = float(content['latitude'])
            longitude = float(content['longitude'])
        except (KeyError, TypeError, ValueError):
            await self.send_json({'type': 'error', 'detail': 'latitude and longitude are required numbers.'})
            return

        heading = content.get('heading')
        speed_kmh = content.get('speed_kmh')

        await self._record_location(user, latitude, longitude, heading, speed_kmh)
        # Note: record_location_ping() already broadcasts to the group via
        # the channel layer, so no explicit send() is needed here.

    # --- group event handlers -------------------------------------------------
    # Method names correspond to the "type" key (dots -> underscores) sent
    # via channel_layer.group_send() from apps.orders/apps.delivery services.

    async def order_status_update(self, event):
        await self.send_json({
            'type': 'status_update',
            'order_id': event['order_id'],
            'status': event['status'],
            'status_display': event['status_display'],
            'updated_at': event['updated_at'],
        })

    async def driver_location_update(self, event):
        await self.send_json({
            'type': 'driver_location',
            'order_id': event['order_id'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'heading': event.get('heading'),
            'speed_kmh': event.get('speed_kmh'),
        })

    # --- DB helpers -------------------------------------------------------
    @database_sync_to_async
    def _get_order(self, order_id):
        from apps.orders.models import Order
        return Order.objects.select_related('customer', 'restaurant__owner', 'driver__user').filter(
            pk=order_id
        ).first()

    @database_sync_to_async
    def _user_can_access_order(self, user, order):
        return (
            order.customer_id == user.id
            or order.restaurant.owner_id == user.id
            or (order.driver_id and order.driver.user_id == user.id)
            or user.is_staff
        )

    @database_sync_to_async
    def _record_location(self, user, latitude, longitude, heading, speed_kmh):
        from apps.delivery.models import DriverProfile
        from apps.delivery.services import record_location_ping

        driver_profile = DriverProfile.objects.filter(user=user).first()
        if driver_profile is None:
            return
        record_location_ping(
            driver=driver_profile, latitude=latitude, longitude=longitude,
            order=self.order, heading=heading, speed_kmh=speed_kmh,
        )


class DriverFleetConsumer(AsyncJsonWebsocketConsumer):
    """
    Optional dashboard channel for restaurant/admin staff: streams every
    available driver's position for a live fleet map, independent of any
    single order. Group name: `fleet_dashboard`.
    """

    async def connect(self):
        user = self.scope['user']
        if not user or not user.is_authenticated or user.role not in ('restaurant_owner', 'admin'):
            await self.close(code=4003)
            return
        self.group_name = 'fleet_dashboard'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def fleet_location_update(self, event):
        await self.send_json(event)
