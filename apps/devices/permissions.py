from rest_framework import permissions

class CanManageDevice(permissions.BasePermission):
    """
    Permissions for device management
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read operations allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Create/Update/Delete only for platform_owner, tenant_admin, branch_manager
        return (
            request.user.is_platform_owner or
            request.user.is_tenant_admin or
            request.user.is_branch_manager
        )
    
    def has_object_permission(self, request, view, obj):
        # Read allowed for everyone (filtered by queryset)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        user = request.user
        
        # Platform owner can manage any device
        if user.is_platform_owner:
            return True
        
        # Tenant admin can manage devices in their tenant
        if user.is_tenant_admin:
            return obj.branch.tenant_id == user.tenant_id
        
        # Branch manager can manage devices in their branch
        if user.is_branch_manager:
            return obj.branch_id == user.branch_id
        
        return False
