from django.urls import path
from .views import MyDriverProfileView, ToggleAvailabilityView, LocationPingView

urlpatterns = [
    path('me/', MyDriverProfileView.as_view(), name='driver-me'),
    path('availability/', ToggleAvailabilityView.as_view(), name='driver-availability'),
    path('location-ping/', LocationPingView.as_view(), name='driver-location-ping'),
]
