from rest_framework import serializers
from .models import POSDevice


class POSDeviceSerializer(serializers.ModelSerializer):
    """POS Device serializer"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    # Full persisted public URL (absolute if possible)
    public_url = serializers.URLField(read_only=True)
    # Request-specific absolute URL (built from request when provided)
    url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = POSDevice
        fields = [
            'id',
            'branch',
            'branch_name',
            'name',
            'device_id',
            'public_url',
            'url',
            'device_type',
            'status',
            'is_active',
            'is_online',
            'last_seen',
            'ip_address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'auth_token', 'last_seen', 'created_at', 'updated_at', 'public_url', 'url']

    def get_url(self, obj):
        request = self.context.get('request')
        # Prefer to build absolute URL with the request (ensures host/port)
        if request is not None:
            try:
                return request.build_absolute_uri(obj.get_absolute_url())
            except Exception:
                pass

        # Fall back to persisted public_url or path-only absolute form
        return obj.public_url or obj.get_absolute_url()


class POSPortalDeviceSerializer(serializers.ModelSerializer):
    """Minimal serializer for POS Portal display"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = POSDevice
        fields = ['id', 'name', 'device_id', 'device_type', 'branch_name', 'status', 'is_online']

