from django.contrib import admin
from .models import Restaurant, MenuCategory, MenuItem


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'average_rating', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'owner__username')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'display_order')
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'is_available')
    list_filter = ('is_available', 'is_vegetarian')
    search_fields = ('name',)
