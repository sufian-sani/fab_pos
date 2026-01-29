from rest_framework import permissions

class CanCreateProduct(permissions.BasePermission):
    """
    Only platform_owner and tenant_admin can create products
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read operations for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only platform_owner and tenant_admin can create/update/delete
        return (
            request.user.is_platform_owner or 
            request.user.is_tenant_admin
        )


class CanCreateCategory(permissions.BasePermission):
    """
    Only platform_owner and tenant_admin can create categories
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read operations for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only platform_owner and tenant_admin can create/update/delete
        return (
            request.user.is_platform_owner or 
            request.user.is_tenant_admin
        )


class CanManageProduct(permissions.BasePermission):
    """
    Check if user can manage specific product
    """
    
    def has_object_permission(self, request, view, obj):
        # Allow read for all authenticated users (filtered by queryset)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Platform owner can manage any product
        if request.user.is_platform_owner:
            return True
        
        # Tenant admin can manage their tenant's products
        if request.user.is_tenant_admin:
            return obj.tenant_id == request.user.tenant_id
        
        return False


class CanManageCategory(permissions.BasePermission):
    """
    Check if user can manage specific category
    """
    
    def has_object_permission(self, request, view, obj):
        # Allow read for all authenticated users (filtered by queryset)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Platform owner can manage any category
        if request.user.is_platform_owner:
            return True
        
        # Tenant admin can manage their tenant's categories
        if request.user.is_tenant_admin:
            return obj.tenant_id == request.user.tenant_id
        
        return False