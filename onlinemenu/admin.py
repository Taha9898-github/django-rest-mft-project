from django.contrib import admin
from .models import Restaurant, ProductCategory, Product, Order, OrderItem


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'owner', 'phone', 'open_time', 'location',
        'rank', 'is_active', 'created_date',
    ]
    list_editable = ['name', 'is_active']
    list_filter = ['is_active', 'rank']
    search_fields = ['name', 'phone', 'location']


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'restaurant', 'is_active']
    list_filter = ['is_active', 'restaurant']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price', 'rank', 'is_active']
    list_filter = ['is_active', 'rank', 'category']
    search_fields = ['name']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'uuid', 'user', 'restaurant', 'is_paid', 'created_date']
    list_filter = ['is_paid', 'restaurant']
    search_fields = ['uuid', 'user__username']
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'amount']
    list_filter = ['order']
    search_fields = ['product__name']
