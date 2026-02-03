from rest_framework.permissions import BasePermission, IsAuthenticated

class IsTenantOwnerOrBranchStaffOrAssigned(BasePermission):
    """Allow access only to tenant owners, branch staff for the branch, or the assigned user."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Platform owner can access everything
        if getattr(user, 'is_platform_owner', False):
            return True

        # Tenant admin/owner: can access devices belonging to their tenant
        tenant_id = getattr(user, 'tenant_id', None)
        device_tenant = obj.tenant_id or (obj.branch.tenant_id if obj.branch else None)
        if tenant_id and device_tenant and tenant_id == device_tenant:
            return True

        # Branch staff: device must be assigned to the same branch
        branch_id = getattr(user, 'branch_id', None)
        if branch_id and obj.branch_id and branch_id == obj.branch_id:
            return True

        # Device-level assignment
        if obj.assigned_to_id and obj.assigned_to_id == getattr(user, 'id', None):
            return True

        return False

    # For list-level filtering, allow access if authenticated; view should further filter queryset
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class POSPortalPermission(IsAuthenticated):
    """
    Permission check for POS Portal access.
    Only users with cashier, branch_manager roles and assigned POS devices can access.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # breakpoint()
        # Platform owner and tenant admin access through regular admin views
        if request.user.is_platform_owner or request.user.is_tenant_admin:
            return True  # Use admin endpoints instead
        
        # Only cashier and branch manager roles can access POS portal
        return request.user.is_cashier or request.user.is_branch_manager
