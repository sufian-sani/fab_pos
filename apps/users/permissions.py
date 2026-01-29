from rest_framework import permissions

class IsPlatformOwner(permissions.BasePermission):
    """Only platform owner can access"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_platform_owner
        )


class IsTenantAdminOrAbove(permissions.BasePermission):
    """Tenant admin or platform owner can access"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (
            request.user.is_platform_owner or 
            request.user.is_tenant_admin
        )


class IsBranchManagerOrAbove(permissions.BasePermission):
    """Branch manager, tenant admin, or platform owner can access"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (
            request.user.is_platform_owner or 
            request.user.is_tenant_admin or 
            request.user.is_branch_manager
        )


class CanManageUser(permissions.BasePermission):
    """Check if user can manage specific user object"""
    
    def has_object_permission(self, request, view, obj):
        # Platform owner can manage anyone
        if request.user.is_platform_owner:
            return True
        
        # Tenant admin can manage users in their tenant
        if request.user.is_tenant_admin:
            return obj.tenant_id == request.user.tenant_id
        
        # Branch manager can manage cashiers in their branch
        if request.user.is_branch_manager:
            return (
                obj.role == 'cashier' and 
                obj.branch_id == request.user.branch_id
            )
        
        # Users can only manage themselves
        return obj.id == request.user.id
