from rest_framework import serializers
from .models import POSDevice
from django.conf import settings


class POSDeviceSerializer(serializers.ModelSerializer):
    """POS Device serializer"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    # Full persisted public URL (absolute if possible)
    public_url = serializers.URLField(read_only=True)
    # Request-specific absolute URL (built from request when provided)
    url = serializers.SerializerMethodField(read_only=True)
    # Absolute login URL for this device
    login_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = POSDevice
        fields = [
            'id',
            'branch',
            'branch_name',
            'name',
            'device_id',
            'public_url',
            'login_url',
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
        read_only_fields = ['id', 'auth_token', 'last_seen', 'created_at', 'updated_at', 'public_url', 'url', 'login_url']

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

    def get_login_url(self, obj):
        request = self.context.get('request')
        path = obj.get_login_path()
        if request is not None:
            try:
                return request.build_absolute_uri(path)
            except Exception:
                pass

        # Fall back to persisted public_url + 'login/' or path-only
        if obj.public_url:
            # ensure single trailing slash
            base = obj.public_url.rstrip('/')
            return base + '/login/' if not base.endswith('/login') else base

        # If SITE_URL is configured
        site = getattr(settings, 'SITE_URL', '')
        if site:
            base = site.rstrip('/')
            return base + path if path.startswith('/') else base + '/' + path

        return path


class DeviceLoginSerializer(serializers.Serializer):
    """Accept either username/password or device credentials (device_id + auth_token)."""
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # Device credentials
    device_id = serializers.CharField(required=False)
    auth_token = serializers.CharField(required=False)

    def validate(self, attrs):
        # Must provide either user credentials or device credentials
        if (attrs.get('username') and attrs.get('password')):
            return attrs
        if attrs.get('device_id') and attrs.get('auth_token'):
            return attrs
        raise serializers.ValidationError('Provide username/password or device_id/auth_token')


class POSPortalDeviceSerializer(serializers.ModelSerializer):
    """Minimal serializer for POS Portal display"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = POSDevice
        fields = ['id', 'name', 'device_id', 'device_type', 'branch_name', 'status', 'is_online']

