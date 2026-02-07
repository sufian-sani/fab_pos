# ============================================================================
# apps/pos/views.py - UPDATED to integrate with your existing code
# ============================================================================

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework import permissions

from apps.pos.models import POSDevice
from apps.pos.serializers import POSDeviceSerializer, DeviceLoginSerializer
from apps.pos.permissions import IsTenantOwnerOrBranchStaffOrAssigned, POSPortalPermission
from apps.tenants.models import Tenant




# ============================================================================
# READ-ONLY DEVICE VIEWSET (Your existing code - keeping it)
# ============================================================================

class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoints for devices (list, retrieve).

    Registered under `devices` namespace.
    """
    serializer_class = POSDeviceSerializer
    permission_classes = [POSPortalPermission]


    def get_queryset(self):
        user = self.request.user
        if user.is_platform_owner:
            return POSDevice.objects.select_related('branch', 'branch__tenant', 'tenant')

        if user.is_tenant_admin:
            return POSDevice.objects.filter(tenant_id=user.tenant_id).select_related('branch', 'tenant')

        if user.is_branch_manager:
            return POSDevice.objects.filter(branch_id=user.branch_id).select_related('branch', 'tenant')
        return POSDevice.objects.none()

# ============================================================================
# ADDITIONAL DEVICE ENDPOINTS
# ============================================================================


class DeviceStatusAPIView(APIView):
    """
    Get device status
    
    GET /api/pos/tenants/{tenant_id}/devices/{device_id}/status/
    
    Headers:
    X-POS-Token: POS-xxxxx (optional)
    """
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, tenant_id, device_id):
        """Get device status"""
        
        device_token = request.META.get('HTTP_X_POS_TOKEN')
        
        try:
            device = POSDevice.objects.select_related(
                'branch',
                'tenant'
            ).get(
                device_id=device_id,
                tenant_id=tenant_id
            )
        except POSDevice.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Device not found',
                    'code': 'DEVICE_NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Basic status
        response_data = {
            'success': True,
            'device_id': device.device_id,
            'name': device.name,
            'status': device.status,
            'is_online': device.is_online,
            'is_active': device.is_active
        }
        
        # If valid token, return detailed info
        if device_token and device.auth_token == device_token:
            response_data.update({
                'branch': {
                    'id': device.branch.id if device.branch else None,
                    'name': device.branch.name if device.branch else None,
                },
                'tenant': {
                    'id': device.tenant.id if device.tenant else None,
                    'name': device.tenant.name if device.tenant else None,
                },
                'last_seen': device.last_seen,
                'device_type': device.device_type,
                'ip_address': device.ip_address
            })
        
        return Response(response_data, status=status.HTTP_200_OK)