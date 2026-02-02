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

from .models import POSDevice
from .serializers import POSDeviceSerializer, DeviceLoginSerializer
from .permissions import IsTenantOwnerOrBranchStaffOrAssigned
from apps.tenants.models import Tenant


# ============================================================================
# POS DEVICE VIEWSET (Your existing code - keeping it)
# ============================================================================

class POSDeviceViewSet(viewsets.ModelViewSet):
    """
    POS Device management
    
    Endpoints:
    - GET /api/pos/devices/manage/ - List devices
    - POST /api/pos/devices/manage/ - Create device
    - GET /api/pos/devices/manage/{id}/ - Get device
    - PUT/PATCH /api/pos/devices/manage/{id}/ - Update device
    - DELETE /api/pos/devices/manage/{id}/ - Delete device
    - POST /api/pos/devices/manage/{id}/activate/ - Activate device
    - POST /api/pos/devices/manage/{id}/deactivate/ - Deactivate device
    - POST /api/pos/devices/manage/{id}/ping/ - Update device status
    - POST /api/pos/devices/manage/{id}/generate_token/ - Generate auth token
    """
    
    serializer_class = POSDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter devices based on user role"""
        user = self.request.user
        
        if user.is_platform_owner:
            return POSDevice.objects.select_related('branch', 'branch__tenant', 'tenant')
        
        if user.is_tenant_admin:
            return POSDevice.objects.filter(
                tenant_id=user.tenant_id
            ).select_related('branch', 'tenant')
        
        if user.is_branch_staff:
            return POSDevice.objects.filter(
                branch__staff=user
            ).select_related('branch', 'tenant')
        
        return POSDevice.objects.none()
    
    def perform_create(self, serializer):
        """Validate branch access before creating device"""
        user = self.request.user
        branch = serializer.validated_data.get('branch')
        
        # Validate access to branch
        if user.is_tenant_admin and branch and branch.tenant_id != user.tenant_id:
            raise PermissionError("Cannot create device for this branch")
        
        if user.is_branch_staff and branch and not branch.staff.filter(id=user.id).exists():
            raise PermissionError("Cannot create device for this branch")
        
        device = serializer.save()
        if not device.auth_token:
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


# ============================================================================
# READ-ONLY DEVICE VIEWSET (Your existing code - keeping it)
# ============================================================================

class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoints for devices (list, retrieve).

    Registered under `devices` namespace.
    """
    serializer_class = POSDeviceSerializer
    permission_classes = [IsAuthenticated]

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
# DEVICE LOGIN VIEW - ENHANCED VERSION
# ============================================================================

class DeviceLoginAPIView(APIView):
    """
    Enhanced device login with multiple authentication modes
    
    POST /api/pos/tenants/{tenant_id}/devices/{device_id}/login/
    
    Supports 3 authentication modes:
    1. User credentials (username + password)
    2. Device credentials (device_id + auth_token)
    3. Simple device login (no credentials - for testing/kiosk mode)
    
    Request Body (all optional):
    {
        "username": "user@example.com",      // Mode 1: User login
        "password": "password",              // Mode 1: User login
        "device_id": "POS-001",              // Mode 2: Device login
        "auth_token": "POS-abc123",          // Mode 2: Device login
        "pin": "1234"                        // Optional PIN for any mode
    }
    
    Response:
    {
        "success": true,
        "token": "drf-token-xxx",            // Only for user login
        "device_token": "POS-abc123",        // Device auth token
        "user": {...},                       // Only for user login
        "device": {...},
        "branch": {...},
        "tenant": {...},
        "session": {...}
    }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, tenant_id=None, device_id=None):
        serializer = DeviceLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get tenant
        tenant = get_object_or_404(Tenant, id=tenant_id, is_active=True)

        # Find target device
        try:
            device = POSDevice.objects.select_related(
                'branch',
                'branch__tenant',
                'tenant',
                'assigned_to'
            ).get(device_id=device_id, is_active=True)
        except POSDevice.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Device not found or inactive',
                    'code': 'DEVICE_NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate tenant match
        device_tenant = device.tenant or (device.branch.tenant if device.branch else None)
        if device_tenant and device_tenant.id != tenant.id:
            return Response(
                {
                    'success': False,
                    'error': 'Device does not belong to this tenant',
                    'code': 'TENANT_MISMATCH'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if device is suspended
        if device.status == 'suspended':
            return Response(
                {
                    'success': False,
                    'error': 'Device is suspended. Contact administrator.',
                    'code': 'DEVICE_SUSPENDED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Optional PIN validation (if device has PIN protection)
        if hasattr(device, 'pin') and device.pin:
            pin = data.get('pin')
            if not pin or device.pin != pin:
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid PIN',
                        'code': 'INVALID_PIN'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Update device status
        now = timezone.now()
        device.last_seen = now
        device.status = 'online'
        
        # Update IP address
        ip_address = self.get_client_ip(request)
        if ip_address:
            device.ip_address = ip_address
        
        device.save()

        # MODE 1: User credentials login
        user = None
        if data.get('username') and data.get('password'):
            user = authenticate(
                request,
                username=data.get('username'),
                password=data.get('password')
            )
            
            if not user:
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid credentials',
                        'code': 'INVALID_CREDENTIALS'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Check user has access to this device
            perm = IsTenantOwnerOrBranchStaffOrAssigned()
            if not perm.has_object_permission(request, self, device):
                return Response(
                    {
                        'success': False,
                        'error': 'Not authorized for this device',
                        'code': 'NOT_AUTHORIZED'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Generate/get user token
            token, _ = Token.objects.get_or_create(user=user)

            # Calculate session expiry
            from datetime import timedelta
            expires_at = now + timedelta(hours=8)

            return Response({
                'success': True,
                'token': token.key,  # DRF token for user authentication
                'device_token': device.auth_token,  # Device token for device authentication
                'user': {
                    'id': user.id,
                    'email': getattr(user, 'email', None),
                    'name': getattr(user, 'get_full_name', lambda: None)() or getattr(user, 'username', None),
                    'role': getattr(user, 'role', None),
                    'tenant_id': getattr(user, 'tenant_id', None),
                },
                'device': {
                    'id': device.id,
                    'device_id': device.device_id,
                    'name': device.name,
                    'device_type': device.device_type,
                    'status': device.status,
                    'is_online': device.is_online,
                    'public_url': device.public_url,
                },
                'branch': {
                    'id': device.branch.id if device.branch else None,
                    'name': device.branch.name if device.branch else None,
                    'code': getattr(device.branch, 'code', None) if device.branch else None,
                    'address': getattr(device.branch, 'address', None) if device.branch else None,
                    'city': getattr(device.branch, 'city', None) if device.branch else None,
                } if device.branch else None,
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'domain': getattr(tenant, 'domain', None),
                },
                'session': {
                    'logged_in_at': now.isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'session_duration_hours': 8
                },
                'redirect_url': device.public_url or request.build_absolute_uri(device.get_login_path())
            }, status=status.HTTP_200_OK)

        # MODE 2: Device credentials (device_id + auth_token)
        if data.get('device_id') and data.get('auth_token'):
            if data.get('device_id') != device.device_id or data.get('auth_token') != device.auth_token:
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid device credentials',
                        'code': 'INVALID_DEVICE_CREDENTIALS'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Calculate session expiry
            from datetime import timedelta
            expires_at = now + timedelta(hours=8)

            # For device credentials, return device info (no user token)
            return Response({
                'success': True,
                'device_token': device.auth_token,
                'device': {
                    'id': device.id,
                    'device_id': device.device_id,
                    'name': device.name,
                    'device_type': device.device_type,
                    'status': device.status,
                    'is_online': device.is_online,
                    'public_url': device.public_url,
                },
                'branch': {
                    'id': device.branch.id if device.branch else None,
                    'name': device.branch.name if device.branch else None,
                    'code': getattr(device.branch, 'code', None) if device.branch else None,
                } if device.branch else None,
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'domain': getattr(tenant, 'domain', None),
                },
                'session': {
                    'logged_in_at': now.isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'session_duration_hours': 8
                },
                'redirect_url': device.public_url or request.build_absolute_uri(device.get_login_path())
            }, status=status.HTTP_200_OK)

        # MODE 3: Simple device login (no credentials - kiosk/demo mode)
        # Generate token if not exists
        if not device.auth_token:
            device.generate_token()
            device.save()

        # Calculate session expiry
        from datetime import timedelta
        expires_at = now + timedelta(hours=8)

        return Response({
            'success': True,
            'device_token': device.auth_token,
            'device': {
                'id': device.id,
                'device_id': device.device_id,
                'name': device.name,
                'device_type': device.device_type,
                'status': device.status,
                'is_online': device.is_online,
                'public_url': device.public_url,
            },
            'branch': {
                'id': device.branch.id if device.branch else None,
                'name': device.branch.name if device.branch else None,
                'code': getattr(device.branch, 'code', None) if device.branch else None,
                'address': getattr(device.branch, 'address', None) if device.branch else None,
                'city': getattr(device.branch, 'city', None) if device.branch else None,
                'phone': getattr(device.branch, 'phone', None) if device.branch else None,
            } if device.branch else None,
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'domain': getattr(tenant, 'domain', None),
            },
            'session': {
                'logged_in_at': now.isoformat(),
                'expires_at': expires_at.isoformat(),
                'session_duration_hours': 8
            }
        }, status=status.HTTP_200_OK)
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================================================
# MY DEVICES VIEW (Your existing code - keeping it)
# ============================================================================

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


# ============================================================================
# ADDITIONAL DEVICE ENDPOINTS
# ============================================================================

class DeviceLogoutAPIView(APIView):
    """
    Device logout
    
    POST /api/pos/tenants/{tenant_id}/devices/{device_id}/logout/
    
    Headers:
    X-POS-Token: POS-xxxxx
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, tenant_id, device_id):
        """Logout POS device"""
        
        device_token = request.META.get('HTTP_X_POS_TOKEN')
        
        if not device_token:
            return Response(
                {
                    'success': False,
                    'error': 'Device token required',
                    'code': 'TOKEN_REQUIRED'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = POSDevice.objects.get(
                device_id=device_id,
                tenant_id=tenant_id,
                auth_token=device_token
            )
        except POSDevice.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Invalid device or token',
                    'code': 'INVALID_DEVICE'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        device.status = 'offline'
        device.save()
        
        return Response(
            {
                'success': True,
                'message': 'Device logged out successfully',
                'device_id': device.device_id
            },
            status=status.HTTP_200_OK
        )


class DeviceHeartbeatAPIView(APIView):
    """
    Device heartbeat
    
    POST /api/pos/tenants/{tenant_id}/devices/{device_id}/heartbeat/
    
    Headers:
    X-POS-Token: POS-xxxxx
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, tenant_id, device_id):
        """Update device heartbeat"""
        
        device_token = request.META.get('HTTP_X_POS_TOKEN')
        
        if not device_token:
            return Response(
                {
                    'success': False,
                    'error': 'Device token required',
                    'code': 'TOKEN_REQUIRED'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = POSDevice.objects.get(
                device_id=device_id,
                tenant_id=tenant_id,
                auth_token=device_token,
                is_active=True
            )
        except POSDevice.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Invalid device or token',
                    'code': 'INVALID_DEVICE'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        now = timezone.now()
        device.last_seen = now
        device.status = 'online'
        device.save(update_fields=['last_seen', 'status'])
        
        return Response(
            {
                'success': True,
                'last_seen': now.isoformat(),
                'is_online': device.is_online,
                'status': device.status
            },
            status=status.HTTP_200_OK
        )


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