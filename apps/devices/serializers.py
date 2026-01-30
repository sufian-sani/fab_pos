from rest_framework import serializers
from .models import Device, DeviceLog
from apps.users.models import User

class DeviceSerializer(serializers.ModelSerializer):
    """Complete device serializer"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    tenant_name = serializers.CharField(source='branch.tenant.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = Device
        fields = [
            'id',
            'branch',
            'branch_name',
            'tenant_name',
            'assigned_to',
            'assigned_to_name',
            'name',
            'device_id',
            'device_type',
            'serial_number',
            'mac_address',
            'model',
            'status',
            'is_active',
            'is_online',
            'last_online',
            'ip_address',
            'os_version',
            'app_version',
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'auth_token', 'last_online', 'created_at', 'updated_at']
    
    def validate_branch(self, value):
        """Validate branch based on user role"""
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        user = request.user
        
        # Platform owner can assign to any branch
        if user.is_platform_owner:
            return value
        
        # Tenant admin can assign to their tenant's branches
        if user.is_tenant_admin:
            if value.tenant_id != user.tenant_id:
                raise serializers.ValidationError(
                    "You can only create devices for branches in your tenant"
                )
            return value
        
        # Branch manager can only assign to their branch
        if user.is_branch_manager:
            if value.id != user.branch_id:
                raise serializers.ValidationError(
                    "You can only create devices for your branch"
                )
            return value
        
        raise serializers.ValidationError("You don't have permission to create devices")
    
    def validate_assigned_to(self, value):
        """Ensure assigned user is a cashier in the same branch"""
        if value:
            branch_id = self.initial_data.get('branch')
            if branch_id:
                if value.role != 'cashier':
                    raise serializers.ValidationError("Device can only be assigned to cashiers")
                if value.branch_id != int(branch_id):
                    raise serializers.ValidationError(
                        "Assigned user must work at the same branch as the device"
                    )
        return value


class DeviceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'branch_name', 'status', 'is_online', 'device_type']


class DeviceLogSerializer(serializers.ModelSerializer):
    """Device log serializer"""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = DeviceLog
        fields = [
            'id',
            'device',
            'device_name',
            'log_type',
            'message',
            'user',
            'user_name',
            'metadata',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']