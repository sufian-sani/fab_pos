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

    # @action(detail=True, methods=['get'], url_path='check_status')
    # def check_status(self, request, tenant_id=None, device_id=None):
    #     # breakpoint() can be used for debugging
    #     return Response({
    #         "success": True,
    #         "message": "Device is online",
    #         "device_id": device_id
    #     })


    # @action(detail=True, methods=['get'], url_path='')
    # def get(self, request, tenant_id=None, device_id=None):
    #     """Get basic device information"""
        
    #     # Get tenant
    #     tenant = get_object_or_404(Tenant, id=tenant_id, is_active=True)
        
    #     # Get device
    #     try:
    #         device = POSDevice.objects.select_related(
    #             'branch',
    #             'branch__tenant',
    #             'tenant',
    #             'assigned_to'
    #         ).get(
    #             device_id=device_id,
    #             is_active=True
    #         )
    #     except POSDevice.DoesNotExist:
    #         return Response(
    #             {
    #                 'success': False,
    #                 'error': 'Device not found or inactive',
    #                 'code': 'DEVICE_NOT_FOUND'
    #             },
    #             status=status.HTTP_404_NOT_FOUND
    #         )
        
    #     # Validate tenant match
    #     device_tenant = device.tenant or (device.branch.tenant if device.branch else None)
    #     if device_tenant and device_tenant.id != tenant.id:
    #         return Response(
    #             {
    #                 'success': False,
    #                 'error': 'Device does not belong to this tenant',
    #                 'code': 'TENANT_MISMATCH'
    #             },
    #             status=status.HTTP_403_FORBIDDEN
    #         )
        
    #     # Build response with basic info
    #     return Response({
    #         'success': True,
    #         'device': {
    #             'id': device.id,
    #             'device_id': device.device_id,
    #             'name': device.name,
    #             'device_type': device.device_type,
    #             'status': device.status,
    #             'is_active': device.is_active,
    #             'is_online': device.is_online,
    #             'public_url': device.public_url,
    #             'last_seen': device.last_seen,
    #         },
    #         'branch': {
    #             'id': device.branch.id if device.branch else None,
    #             'name': device.branch.name if device.branch else None,
    #             'code': getattr(device.branch, 'code', None) if device.branch else None,
    #             'address': getattr(device.branch, 'address', None) if device.branch else None,
    #             'city': getattr(device.branch, 'city', None) if device.branch else None,
    #             'state': getattr(device.branch, 'state', None) if device.branch else None,
    #             'phone': getattr(device.branch, 'phone', None) if device.branch else None,
    #             'email': getattr(device.branch, 'email', None) if device.branch else None,
    #         } if device.branch else None,
    #         'tenant': {
    #             'id': tenant.id,
    #             'name': tenant.name,
    #             'domain': getattr(tenant, 'domain', None),
    #             'slug': getattr(tenant, 'slug', None),
    #         },
    #         'assigned_to': {
    #             'id': device.assigned_to.id if device.assigned_to else None,
    #             'name': getattr(device.assigned_to, 'get_full_name', lambda: None)() if device.assigned_to else None,
    #             'email': getattr(device.assigned_to, 'email', None) if device.assigned_to else None,
    #         } if device.assigned_to else None
    #     }, status=status.HTTP_200_OK)

    # @action(detail=False, methods=['get'], url_path='check_status')
    # def checkStatus(self, request, tenant_id, device_id):
    #     breakpoint()
    #     return Response({
    #         'sidyhsd':"sdfhsdf"
    #     })


    """
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
        # Get client IP address from request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    """