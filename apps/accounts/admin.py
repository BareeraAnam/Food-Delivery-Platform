from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, RestaurantOwnerProfile, CustomerProfile, DeviceToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'is_active', 'referral_code')
    list_filter = ('role', 'is_active', 'is_phone_verified')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Platform info', {'fields': ('role', 'phone_number', 'is_phone_verified', 'referral_code', 'referred_by')}),
    )


admin.site.register(RestaurantOwnerProfile)
admin.site.register(CustomerProfile)
admin.site.register(DeviceToken)
