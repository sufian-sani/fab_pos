from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    
    list_display = [
        'email', 
        'username', 
        'get_full_name', 
        'role', 
        'tenant', 
        'branch', 
        'is_active',
        'date_joined'
    ]
    
    list_filter = ['role', 'is_active', 'is_staff', 'tenant', 'date_joined']
    
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
    
    readonly_fields = ['date_joined', 'last_login']
    
    fieldsets = (
        ('Login Information', {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Role & Access', {
            'fields': ('role', 'tenant', 'branch')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'fields': ('email', 'username', 'password1', 'password2')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Role & Access', {
            'fields': ('role', 'tenant', 'branch')
        }),
    )
    
    ordering = ['-date_joined']
    filter_horizontal = ['groups', 'user_permissions']
    
    def get_queryset(self, request):
        """Filter users based on role"""
        qs = super().get_queryset(request)
        
        # Platform owner sees all users
        if request.user.is_platform_owner:
            return qs
        
        # Tenant admin sees only their users
        if request.user.is_tenant_admin:
            return qs.filter(tenant=request.user.tenant)
        
        # Others see only themselves
        return qs.filter(id=request.user.id)