from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import POSDevice
from .serializers import POSDeviceSerializer


# ============================================================================
# POS DEVICE VIEWSET
# ============================================================================

class POSDeviceViewSet(viewsets.ModelViewSet):
    """
    POS Device management
    
    Endpoints:
    - GET /api/pos/devices/ - List devices
    - POST /api/pos/devices/ - Create device
    - GET /api/pos/devices/{id}/ - Get device
    - PUT/PATCH /api/pos/devices/{id}/ - Update device
    - DELETE /api/pos/devices/{id}/ - Delete device
    - POST /api/pos/devices/{id}/activate/ - Activate device
    - POST /api/pos/devices/{id}/deactivate/ - Deactivate device
    - POST /api/pos/devices/{id}/ping/ - Update device status
    - POST /api/pos/devices/{id}/generate_token/ - Generate auth token
    """
    
    serializer_class = POSDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter devices based on user role"""
        user = self.request.user
        
        if user.is_platform_owner:
            return POSDevice.objects.select_related('branch', 'branch__tenant')
        
        if user.is_tenant_admin:
            return POSDevice.objects.filter(
                branch__tenant_id=user.tenant_id
            ).select_related('branch')
        
        if user.is_branch_staff:
            return POSDevice.objects.filter(
                branch__staff=user
            ).select_related('branch')
        
        return POSDevice.objects.none()
    
    def perform_create(self, serializer):
        """Validate branch access before creating device"""
        user = self.request.user
        branch = serializer.validated_data.get('branch')
        
        # Validate access to branch
        if user.is_tenant_admin and branch.tenant_id != user.tenant_id:
            raise PermissionError("Cannot create device for this branch")
        
        if user.is_branch_staff and not branch.staff.filter(id=user.id).exists():
            raise PermissionError("Cannot create device for this branch")
        
        device = serializer.save()
        device.generate_token()
        device.save()
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate POS device"""
        device = self.get_object()
        device.is_active = True
        device.status = 'online'
        device.save()
        
        serializer = self.get_serializer(device)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate POS device"""
        device = self.get_object()
        device.is_active = False
        device.status = 'offline'
        device.save()
        
        serializer = self.get_serializer(device)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ping(self, request, pk=None):
        """Update device last seen timestamp"""
        device = self.get_object()
        device.last_seen = timezone.now()
        device.status = 'online'
        
        # Optionally update IP address
        ip = request.META.get('REMOTE_ADDR')
        if ip:
            device.ip_address = ip
        
        device.save()
        
        return Response({
            'status': 'success',
            'last_seen': device.last_seen,
            'is_online': device.is_online
        })
    
    @action(detail=True, methods=['post'])
    def generate_token(self, request, pk=None):
        """Generate new authentication token"""
        device = self.get_object()
        token = device.generate_token()
        device.save()
        
        return Response({
            'device_id': device.device_id,
            'auth_token': token
        })
    
    @action(detail=False, methods=['get'])
    def online(self, request):
        """Get all online devices"""
        devices = self.get_queryset().filter(status='online')
        serializer = self.get_serializer(devices, many=True)
        return Response(serializer.data)
