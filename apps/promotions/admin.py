from django.contrib import admin
from .models import PromoCode, PromoUsage, ReferralReward


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'valid_from', 'valid_until')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)


@admin.register(PromoUsage)
class PromoUsageAdmin(admin.ModelAdmin):
    list_display = ('promo_code', 'user', 'order', 'discount_applied', 'created_at')


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'reward_amount', 'status', 'granted_at')
    list_filter = ('status',)
