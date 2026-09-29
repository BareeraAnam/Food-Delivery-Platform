from django.contrib import admin
from .models import DriverProfile, DriverLocationPing


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_type', 'is_verified', 'is_available', 'average_rating', 'total_deliveries')
    list_filter = ('is_verified', 'is_available', 'vehicle_type')


@admin.register(DriverLocationPing)
class DriverLocationPingAdmin(admin.ModelAdmin):
    list_display = ('driver', 'order', 'latitude', 'longitude', 'recorded_at')
    readonly_fields = [f.name for f in DriverLocationPing._meta.fields]
