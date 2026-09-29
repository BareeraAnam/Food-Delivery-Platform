from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import permissions


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/restaurants/', include('apps.restaurants.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/delivery/', include('apps.delivery.urls')),
    path('api/v1/reviews/', include('apps.reviews.urls')),
    path('api/v1/promotions/', include('apps.promotions.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
