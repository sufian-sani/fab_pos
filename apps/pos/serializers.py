from rest_framework import serializers
from .models import POSDevice


class POSDeviceSerializer(serializers.ModelSerializer):
    """POS Device serializer"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = POSDevice
        fields = [
            'id',
            'branch',
            'branch_name',
            'name',
            'device_id',
            'device_type',
            'status',
            'is_active',
            'is_online',
            'last_seen',
            'ip_address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'auth_token', 'last_seen', 'created_at', 'updated_at']


class POSPortalDeviceSerializer(serializers.ModelSerializer):
    """Minimal serializer for POS Portal display"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = POSDevice
        fields = ['id', 'name', 'device_id', 'device_type', 'branch_name', 'status', 'is_online']

