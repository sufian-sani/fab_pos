from django.utils.deprecation import MiddlewareMixin

class TenantContextMiddleware(MiddlewareMixin):
    """Add tenant context to every request"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Add tenant to request
            request.tenant = request.user.tenant
            request.is_platform_owner = request.user.is_platform_owner
            request.is_tenant_admin = request.user.is_tenant_admin
        else:
            request.tenant = None
            request.is_platform_owner = False
            request.is_tenant_admin = False
