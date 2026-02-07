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


class BasePosDeviceAPIView(viewsets.ViewSet):

    permission_classes = [POSPortalPermission]

    lookup_field = 'device_id'

    def get_object(self):
        tenant_id = self.kwargs['tenant_id']
        device_id = self.kwargs['device_id']

        device = get_object_or_404(
            POSDevice.objects.select_related('branch', 'tenant', 'assigned_to'),
            device_id=device_id,
            is_active=True
        )

        # tenant validation
        device_tenant = device.tenant or (device.branch.tenant if device.branch else None)
        if device_tenant.id != int(tenant_id):
            raise PermissionDenied("Tenant mismatch")

        return device

    def retrieve(self, request, tenant_id=None, device_id=None):
        device = self.get_object()
        tenant = device.tenant or (device.branch.tenant if device.branch else None)

        return Response({
            'success': True,
            'device': {
                'id': device.id,
                'device_id': device.device_id,
                'name': device.name,
                'device_type': device.device_type,
                'status': device.status,
                'is_active': device.is_active,
                'is_online': device.is_online,
                'public_url': device.public_url,
                'last_seen': device.last_seen,
            },
            'branch': {
                'id': device.branch.id if device.branch else None,
                'name': device.branch.name if device.branch else None,
                'code': getattr(device.branch, 'code', None) if device.branch else None,
                'address': getattr(device.branch, 'address', None) if device.branch else None,
                'city': getattr(device.branch, 'city', None) if device.branch else None,
                'state': getattr(device.branch, 'state', None) if device.branch else None,
                'phone': getattr(device.branch, 'phone', None) if device.branch else None,
                'email': getattr(device.branch, 'email', None) if device.branch else None,
            } if device.branch else None,
            'tenant': {
                'id': tenant.id if tenant else None,
                'name': tenant.name if tenant else None,
                'domain': getattr(tenant, 'domain', None) if tenant else None,
                'slug': getattr(tenant, 'slug', None) if tenant else None,
            },
            'assigned_to': {
                'id': device.assigned_to.id if device.assigned_to else None,
                'name': device.assigned_to.get_full_name() if device.assigned_to else None,
                'email': device.assigned_to.email if device.assigned_to else None,
            } if device.assigned_to else None
        }, status=status.HTTP_200_OK)