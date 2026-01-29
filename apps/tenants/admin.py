from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Tenant Admin - Platform Owner can manage all tenants"""
    
    list_display = [
        'name', 
        'email', 
        'subscription_plan', 
        'max_branches', 
        'user_count',
        'is_active',
        'created_at'
    ]
    
    list_filter = ['subscription_plan', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'max_branches', 'max_devices')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_count(self, obj):
        """Show number of users"""
        return obj.users.count()
    user_count.short_description = 'Users'
    
    def get_queryset(self, request):
        """Platform owner sees all, tenant admin sees only theirs"""
        qs = super().get_queryset(request)
        
        if request.user.is_platform_owner:
            return qs  # See all tenants
        
        if request.user.is_tenant_admin:
            return qs.filter(id=request.user.tenant_id)  # See only their tenant
        
        return qs.none()  # Others see nothing
    
    def has_add_permission(self, request):
        """Only platform owner can add tenants"""
        return request.user.is_platform_owner
    
    def has_delete_permission(self, request, obj=None):
        """Only platform owner can delete tenants"""
        return request.user.is_platform_owner
