from django.contrib import admin
from .models import POSDevice


@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch', 'device_type', 'status', 'is_online', 'is_active']
    list_filter = ['status', 'device_type', 'is_active', 'branch__tenant']
    search_fields = ['name', 'device_id', 'branch__name']
    readonly_fields = ['auth_token', 'last_seen', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('branch', 'name', 'device_id', 'device_type')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'last_seen', 'ip_address')
        }),
        ('Authentication', {
            'fields': ('auth_token',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
