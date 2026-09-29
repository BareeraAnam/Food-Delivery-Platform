# Food Delivery Platform — Backend

Django + Django REST Framework + Django Channels (WebSockets) + Celery (+ Celery Beat)

## Features implemented
- Restaurant & menu management (owners manage categories/items, public search)
- Real-time order tracking over WebSockets (Django Channels, groups/rooms per order)
- Delivery driver GPS tracking + nearest-driver auto-assignment (Haversine, no PostGIS needed)
- Ratings & reviews (restaurant + driver, tied to delivered orders only)
- Promo codes & referral system, with Celery Beat auto-expiry/activation
- Push notifications via Firebase Cloud Messaging (async, through Celery)
- JWT auth (role-based: customer / restaurant_owner / driver / admin)

## Project layout
```
config/            settings, urls, asgi (Channels), wsgi, celery app + beat schedule
apps/
  common/           base model, geo (Haversine) utils, shared permissions, exception handler
  accounts/         custom User model, roles, JWT auth, device tokens
  restaurants/       Restaurant, MenuCategory, MenuItem + nearby search
  orders/           Order state machine, checkout, status transitions, service layer
  delivery/         DriverProfile, GPS pings, nearest-driver assignment
  tracking/         Channels consumers (order room + driver GPS streaming) + JWT ws middleware
  reviews/          Review model + auto rating recalculation signal
  promotions/       PromoCode, ReferralReward, Celery Beat tasks
  notifications/     FCM integration, NotificationLog, async Celery task
```

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # edit values as needed

# Redis is required for both Channels and Celery
redis-server &

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver           # plain HTTP dev server

# In separate terminals for the full real-time stack:
daphne -b 0.0.0.0 -p 8000 config.asgi:application   # ASGI server (HTTP + WebSocket)
celery -A config worker -l info                      # async tasks (notifications, etc.)
celery -A config beat -l info                        # scheduled tasks (promo expiry, cleanup)
```

Or with Docker:
```bash
docker compose up --build
```

## Firebase Cloud Messaging setup
1. Create a Firebase project → Project settings → Service accounts → Generate new private key.
2. Save the JSON as `firebase-service-account.json` in the project root (path configurable via `FCM_CREDENTIALS_FILE` in `.env`).
3. Without this file, push notifications are logged locally instead of sent — the rest of the app still works.

## Key API endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register/` | Register (customer/restaurant_owner/driver), supports `referral_code` |
| POST | `/api/v1/auth/login/` | Obtain JWT access + refresh tokens |
| GET  | `/api/v1/restaurants/nearby/?lat=..&lon=..&radius_km=8` | Geolocation restaurant search |
| POST | `/api/v1/orders/checkout/` | Place an order (complex validation: availability, min order, promo) |
| PATCH| `/api/v1/orders/<id>/status/` | Move an order through its status state machine |
| POST | `/api/v1/delivery/availability/` | Driver toggles online/offline |
| POST | `/api/v1/promotions/validate/` | Preview a promo code's discount before checkout |
| POST | `/api/v1/reviews/` | Review a delivered order (restaurant + optional driver rating) |
| WS   | `ws://host/ws/orders/<order_id>/?token=<jwt>` | Live order status + driver GPS stream |

Interactive API docs: `/api/docs/` (Swagger).

## WebSocket protocol (order tracking)
Connect: `ws://host/ws/orders/<order_id>/?token=<jwt_access_token>`

Server → client:
```json
{"type": "status_update", "status": "on_the_way", "status_display": "On the Way", "updated_at": "..."}
{"type": "driver_location", "latitude": 24.86, "longitude": 67.01, "heading": 180, "speed_kmh": 22}
```

Client → server (driver app only):
```json
{"action": "location_update", "latitude": 24.86, "longitude": 67.01, "heading": 180, "speed_kmh": 22}
```

## Notes on design decisions
- **UUID primary keys** everywhere public-facing, so order/restaurant IDs aren't guessable/enumerable.
- **Haversine instead of PostGIS**: keeps the project runnable on plain SQLite/Postgres without GDAL. Swap to PostGIS `ST_DWithin` in `apps/delivery/services.py` and `apps/restaurants/views.py` if the fleet/catalog grows large enough to need spatial indexes.
- **Service layer** (`services.py` in orders/delivery/promotions): business logic lives outside views/serializers so it's reusable from the WebSocket consumers, Celery tasks, and the admin — not just HTTP views.
- **Order status machine** is enforced server-side (`Order.VALID_TRANSITIONS`), not just documented — an illegal transition is rejected with a 400, not silently accepted.
- **Async side-effects** (push notifications, referral rewards) always go through Celery `.delay()`, never inline, so the checkout/status-update endpoints stay fast.

## Running tests
```bash
python manage.py test
```
(Add your test suite under each app's `tests.py` / `tests/` package — none is bundled by default.)
