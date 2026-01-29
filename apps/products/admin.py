from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'display_order', 'is_active']
    list_filter = ['tenant', 'is_active']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price', 'is_available', 'is_active']
    list_filter = ['tenant', 'category', 'is_available', 'is_active']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['created_at', 'updated_at']