from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions

from .models import POSDevice
from .serializers import POSDeviceSerializer, DeviceLoginSerializer
from .permissions import IsTenantOwnerOrBranchStaffOrAssigned


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


# ---------------------------------------------------------------------------
# Read-only DeviceViewSet (public-facing) - exposes `list` and `retrieve`
# ---------------------------------------------------------------------------
class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoints for devices (list, retrieve).

    Registered under `devices` namespace.
    """
    serializer_class = POSDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_owner:
            return POSDevice.objects.select_related('branch', 'branch__tenant')

        if user.is_tenant_admin:
            return POSDevice.objects.filter(tenant_id=user.tenant_id).select_related('branch')

        if user.is_branch_manager:
            return POSDevice.objects.filter(branch_id=user.branch_id).select_related('branch')

        return POSDevice.objects.none()


class DeviceLoginAPIView(APIView):
    """POST endpoint to login to a device.

    URL: /pos/tenants/<tenant_id>/devices/<device_id>/login/
    Accepts username/password or device credentials (device_id + auth_token).
    Returns token (DRF Token) and user role info when user creds used.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, tenant_id=None, device_id=None):
        serializer = DeviceLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Find target device
        try:
            device = POSDevice.objects.select_related('branch', 'tenant').get(device_id=device_id)
        except POSDevice.DoesNotExist:
            return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        # Simple tenant id check
        device_tenant_id = device.tenant_id or (device.branch.tenant_id if device.branch else None)
        if tenant_id and str(device_tenant_id) != str(tenant_id):
            return Response({'detail': 'Device not in tenant'}, status=status.HTTP_403_FORBIDDEN)

        # If username/password provided
        user = None
        if data.get('username') and data.get('password'):
            user = authenticate(request, username=data.get('username'), password=data.get('password'))
            if not user:
                return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

            # Check access
            perm = IsTenantOwnerOrBranchStaffOrAssigned()
            if not perm.has_object_permission(request, self, device):
                return Response({'detail': 'Not authorized for this device'}, status=status.HTTP_403_FORBIDDEN)

            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': getattr(user, 'email', None),
                    'role': getattr(user, 'role', None),
                    'tenant_id': getattr(user, 'tenant_id', None),
                },
                'device': {
                    'id': device.id,
                    'name': device.name,
                    'device_id': device.device_id,
                    'public_url': device.public_url,
                },
                'redirect_url': device.public_url or request.build_absolute_uri(device.get_login_path())
            })

        # Device credential flow
        if data.get('device_id') and data.get('auth_token'):
            if data.get('device_id') != device.device_id or data.get('auth_token') != device.auth_token:
                return Response({'detail': 'Invalid device credentials'}, status=status.HTTP_400_BAD_REQUEST)

            # For device credentials we return device info (no user token)
            return Response({
                'device': {
                    'id': device.id,
                    'name': device.name,
                    'device_id': device.device_id,
                    'public_url': device.public_url,
                },
                'redirect_url': device.public_url or request.build_absolute_uri(device.get_login_path())
            })

        return Response({'detail': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)


class MyDevicesAPIView(APIView):
    """Return devices the authenticated user can access."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = POSDevice.objects.none()

        if getattr(user, 'is_platform_owner', False):
            qs = POSDevice.objects.select_related('branch', 'tenant').all()
        else:
            # Tenant admin/owner
            if getattr(user, 'is_tenant_admin', False) and user.tenant_id:
                qs = qs | POSDevice.objects.filter(tenant_id=user.tenant_id)

            # Branch staff
            if getattr(user, 'branch_id', None):
                qs = qs | POSDevice.objects.filter(branch_id=user.branch_id)

            # Assigned devices
            qs = qs | POSDevice.objects.filter(assigned_to_id=user.id)

        qs = qs.distinct().select_related('branch', 'tenant')
        serializer = POSDeviceSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
