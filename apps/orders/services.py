from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Order, OrderItem, OrderStatusHistory


@transaction.atomic
def create_order_from_checkout(*, user, validated_data):
    """
    Builds an Order + OrderItems from a validated CheckoutSerializer payload.
    Wrapped in a transaction so a failure partway through never leaves an
    order with missing items or a promo code that was validated but never
    actually applied.
    """
    restaurant = validated_data['_restaurant']
    resolved_items = validated_data['_resolved_items']
    subtotal = validated_data['_subtotal']
    discount = validated_data['_discount']
    promo = validated_data['_promo']

    delivery_fee = restaurant.delivery_fee
    total_amount = max(subtotal + delivery_fee - discount, Decimal('0.00'))

    order = Order.objects.create(
        customer=user,
        restaurant=restaurant,
        delivery_address=validated_data['delivery_address'],
        delivery_latitude=validated_data['delivery_latitude'],
        delivery_longitude=validated_data['delivery_longitude'],
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount_amount=discount,
        total_amount=total_amount,
        promo_code=promo,
        payment_method=validated_data['payment_method'],
        special_instructions=validated_data.get('special_instructions', ''),
    )

    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            menu_item=item['menu_item'],
            item_name_snapshot=item['menu_item'].name,
            unit_price_snapshot=item['menu_item'].price,
            quantity=item['quantity'],
            notes=item.get('notes', ''),
        )
        for item in resolved_items
    ])

    OrderStatusHistory.objects.create(order=order, status=Order.Status.PLACED, changed_by=user)

    if promo:
        from apps.promotions.services import register_promo_usage
        register_promo_usage(promo=promo, user=user, order=order)

    # Async side-effects — never block the HTTP response on these.
    from apps.notifications.tasks import send_push_notification_task
    send_push_notification_task.delay(
        user_id=str(restaurant.owner_id),
        title='New order received! 🛎️',
        body=f'Order #{str(order.id)[:8]} — {resolved_items.__len__()} item(s).',
        data={'type': 'new_order', 'order_id': str(order.id)},
    )

    return order


@transaction.atomic
def transition_order_status(*, order, new_status, changed_by, note=''):
    """
    Applies a validated status transition, records history, broadcasts the
    change over the order's WebSocket group, and fires the right async
    side-effects (driver assignment, notifications).
    """
    order.status = new_status
    if new_status == Order.Status.DELIVERED:
        order.delivered_at = timezone.now()
    order.save(update_fields=['status', 'delivered_at', 'updated_at'] if new_status == Order.Status.DELIVERED else ['status', 'updated_at'])

    OrderStatusHistory.objects.create(order=order, status=new_status, changed_by=changed_by, note=note)

    _broadcast_order_update(order)

    from apps.notifications.tasks import send_push_notification_task
    send_push_notification_task.delay(
        user_id=str(order.customer_id),
        title=f'Order update: {order.get_status_display()}',
        body=f'Your order #{str(order.id)[:8]} is now "{order.get_status_display()}".',
        data={'type': 'order_status', 'order_id': str(order.id), 'status': new_status},
    )

    if new_status == Order.Status.READY_FOR_PICKUP:
        from apps.delivery.services import assign_nearest_driver
        assign_nearest_driver(order)

    return order


def _broadcast_order_update(order):
    """Pushes the new status to everyone subscribed to this order's
    WebSocket group (customer app, restaurant dashboard, driver app)."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return  # channel layer not configured (e.g. running tests) — skip

    async_to_sync(channel_layer.group_send)(
        f'order_{order.id}',
        {
            'type': 'order.status_update',
            'order_id': str(order.id),
            'status': order.status,
            'status_display': order.get_status_display(),
            'updated_at': order.updated_at.isoformat(),
        },
    )
