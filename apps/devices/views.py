from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import Device, DeviceLog
from .serializers import (
    DeviceSerializer,
    DeviceListSerializer,
    DeviceLogSerializer
)
from .permissions import CanManageDevice


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for POS Device management
    
    Permissions:
    - CREATE: platform_owner, tenant_admin, branch_manager
    - READ: All authenticated users (filtered by tenant/branch)
    - UPDATE: platform_owner, tenant_admin, branch_manager (own branch)
    - DELETE: platform_owner, tenant_admin
    
    Endpoints:
    - GET /api/devices/ - List devices
    - POST /api/devices/ - Create device
    - GET /api/devices/{id}/ - Get device details
    - PUT /api/devices/{id}/ - Update device
    - DELETE /api/devices/{id}/ - Delete device
    - GET /api/devices/by_branch/ - Get devices by branch
    - GET /api/devices/online/ - Get online devices
    - POST /api/devices/{id}/heartbeat/ - Device heartbeat
    - POST /api/devices/{id}/assign_user/ - Assign user to device
    - GET /api/devices/{id}/logs/ - Get device logs
    """
    
    queryset = Device.objects.select_related('branch', 'branch__tenant', 'assigned_to')
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated, CanManageDevice]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['branch', 'status', 'device_type', 'is_active']
    search_fields = ['name', 'device_id', 'serial_number']
    ordering_fields = ['name', 'created_at', 'last_online']
    ordering = ['branch', 'name']
    
    def get_queryset(self):
        """Filter devices based on user role"""
        user = self.request.user
        
        # Platform owner sees all devices
        if user.is_platform_owner:
            return self.queryset
        
        # Tenant admin sees all devices in their tenant
        if user.is_tenant_admin:
            return self.queryset.filter(branch__tenant=user.tenant)
        
        # Branch manager sees devices in their branch
        if user.is_branch_manager:
            return self.queryset.filter(branch=user.branch)
        
        # Cashiers see only their assigned device
        if user.role == 'cashier':
            return self.queryset.filter(assigned_to=user)
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DeviceListSerializer
        return DeviceSerializer
    
    def perform_create(self, serializer):
        """Auto-set branch for branch managers"""
        user = self.request.user
        
        if user.is_branch_manager:
            serializer.save(branch=user.branch)
        else:
            serializer.save()
        
        # Log device creation
        device = serializer.instance
        DeviceLog.objects.create(
            device=device,
            log_type='online',
            message=f'Device {device.name} created',
            user=user
        )
    
    @action(detail=False, methods=['get'])
    def by_branch(self, request):
        """
        Get devices grouped by branch
        GET /api/devices/by_branch/
        """
        devices = self.get_queryset()
        
        # Group by branch
        branches = {}
        for device in devices:
            branch_id = device.branch_id
            if branch_id not in branches:
                branches[branch_id] = {
                    'branch_id': branch_id,
                    'branch_name': device.branch.name,
                    'devices': []
                }
            branches[branch_id]['devices'].append(
                DeviceListSerializer(device).data
            )
        
        return Response(list(branches.values()))
    
    @action(detail=False, methods=['get'])
    def online(self, request):
        """
        Get only online devices
        GET /api/devices/online/
        """
        online_devices = [d for d in self.get_queryset() if d.is_online]
        serializer = self.get_serializer(online_devices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """
        Device heartbeat - update online status
        POST /api/devices/{id}/heartbeat/
        Body: {"ip_address": "192.168.1.100"} (optional)
        """
        device = self.get_object()
        ip_address = request.data.get('ip_address')
        
        device.update_online_status(ip_address)
        
        # Log heartbeat
        DeviceLog.objects.create(
            device=device,
            log_type='online',
            message='Device heartbeat received',
            user=request.user,
            metadata={'ip_address': ip_address}
        )
        
        return Response({
            'message': 'Heartbeat received',
            'device': DeviceSerializer(device).data
        })
    
    @action(detail=True, methods=['post'])
    def assign_user(self, request, pk=None):
        """
        Assign user (cashier) to device
        POST /api/devices/{id}/assign_user/
        Body: {"user_id": 5}
        """
        device = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            
            if user.role != 'cashier':
                return Response(
                    {'error': 'User must be a cashier'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if user.branch_id != device.branch_id:
                return Response(
                    {'error': 'User must work at the same branch'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            device.assigned_to = user
            device.save()
            
            # Log assignment
            DeviceLog.objects.create(
                device=device,
                log_type='login',
                message=f'Device assigned to {user.get_full_name()}',
                user=request.user
            )
            
            return Response({
                'message': f'Device assigned to {user.get_full_name()}',
                'device': DeviceSerializer(device).data
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Get device logs
        GET /api/devices/{id}/logs/
        Query: ?log_type=login&limit=100
        """
        device = self.get_object()
        logs = device.logs.all()
        
        # Filter by log type if provided
        log_type = request.query_params.get('log_type')
        if log_type:
            logs = logs.filter(log_type=log_type)
        
        # Limit results
        limit = int(request.query_params.get('limit', 100))
        logs = logs[:limit]
        
        serializer = DeviceLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get device statistics
        GET /api/devices/stats/
        """
        queryset = self.get_queryset()
        
        online_devices = [d for d in queryset if d.is_online]
        
        stats = {
            'total_devices': queryset.count(),
            'online_devices': len(online_devices),
            'offline_devices': queryset.count() - len(online_devices),
            'by_status': {},
            'by_type': {},
            'by_branch': {}
        }
        
        # Count by status
        for status_code, status_name in Device.STATUS_CHOICES:
            stats['by_status'][status_code] = queryset.filter(status=status_code).count()
        
        # Count by type
        for type_code, type_name in Device.DEVICE_TYPE_CHOICES:
            stats['by_type'][type_code] = queryset.filter(device_type=type_code).count()
        
        # Count by branch
        for device in queryset:
            branch_name = device.branch.name
            if branch_name not in stats['by_branch']:
                stats['by_branch'][branch_name] = 0
            stats['by_branch'][branch_name] += 1
        
        return Response(stats)