from django.contrib import admin
from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'quantity', 'minimum_quantity', 'stock_status']
    list_filter = ['branch']
    search_fields = ['product__name', 'branch__name']

    def stock_status(self, obj):
        return obj.stock_status

    stock_status.short_description = 'Status'