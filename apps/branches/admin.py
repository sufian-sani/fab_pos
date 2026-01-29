from django.contrib import admin
from .models import Branch

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'tenant', 'city', 'is_active', 'created_at']
    list_filter = ['tenant', 'city', 'country', 'is_active']
    search_fields = ['name', 'code', 'address', 'city']
    readonly_fields = ['created_at', 'updated_at']