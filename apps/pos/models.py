from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


class POSDevice(models.Model):
    """
    POS Device/Terminal under a branch
    Each branch can have multiple POS devices
    """
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('maintenance', 'Maintenance'),
        ('suspended', 'Suspended'),
    ]
    
    # Branch is optional; a device may be linked directly to a tenant
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        related_name='devices',
        null=True,
        blank=True,
    )
    # Tenant FK for multi-tenant awareness (preferred source for building URLs)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='devices',
        null=True,
        blank=True,
        db_index=True,
    )
    
    # Device Info
    name = models.CharField(max_length=255, help_text="e.g., Counter 1, Drive-thru")
    device_id = models.CharField(max_length=100, unique=True, help_text="Unique device identifier")
    
    # Device Type
    device_type = models.CharField(
        max_length=50,
        choices=[
            ('tablet', 'Tablet'),
            ('desktop', 'Desktop'),
            ('mobile', 'Mobile'),
        ],
        default='tablet'
    )
    
    # Authentication
    auth_token = models.CharField(max_length=255, unique=True, blank=True)

    # Device-level assignment (optional): specific user assigned to this device
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_devices'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline'
    )
    is_active = models.BooleanField(default=True)
    
    # Connection
    last_seen = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Public absolute URL for this device (populated automatically)
    public_url = models.URLField(max_length=1024, blank=True)
    
    class Meta:
        db_table = 'pos_devices'
        verbose_name = 'POS Device'
        verbose_name_plural = 'POS Devices'
        ordering = ['branch', 'name']
        indexes = [
            models.Index(fields=['branch', 'is_active']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        branch_name = self.branch.name if self.branch else 'NoBranch'
        tenant_name = getattr(self.tenant, 'name', None) or (getattr(self.branch, 'tenant', None) and getattr(self.branch.tenant, 'name', None))
        prefix = tenant_name or branch_name
        return f"{prefix} - {self.name}"
    
    @property
    def is_online(self):
        """Check if device is online"""
        if self.status != 'online':
            return False
        
        if not self.last_seen:
            return False
        
        # Consider offline if no ping in last 5 minutes
        from datetime import timedelta
        threshold = timezone.now() - timedelta(minutes=5)
        return self.last_seen > threshold
    
    def generate_token(self):
        """Generate authentication token"""
        import uuid
        self.auth_token = f"POS-{uuid.uuid4().hex}"
        return self.auth_token

    def save(self, *args, **kwargs):
        if not self.auth_token:
            self.generate_token()
        # Ensure tenant is set from branch if not explicitly provided
        if not self.tenant and self.branch is not None:
            try:
                self.tenant = self.branch.tenant
            except Exception:
                pass

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """
        Return canonical path for this device.

        - If tenant has a domain, use path like `/devices/<device_id>/` (tenant domain will be used
          as the host when building absolute URLs).
        - Otherwise use `/tenants/<tenant.slug or tenant.id>/devices/<device_id>/`.
        """
        # Return canonical path for this device within the POS area.
        # If tenant has a domain, the host will be that domain and path can be short.
        tenant = self.tenant or (self.branch.tenant if self.branch and getattr(self.branch, 'tenant', None) else None)
        tenant_domain = getattr(tenant, 'domain', None) if tenant else None
        slug = getattr(tenant, 'slug', None) or (getattr(tenant, 'id', None) if tenant else None)

        if tenant and tenant_domain:
            return f"/devices/{self.device_id}/"

        if slug:
            return f"/pos/tenants/{slug}/devices/{self.device_id}/"

        # Fallback to a path-only URL using device id
        return f"/pos/devices/{self.device_id}/"

    def get_login_path(self):
        """Return the login path for this device (path-only)."""
        tenant = self.tenant or (self.branch.tenant if self.branch and getattr(self.branch, 'tenant', None) else None)
        tenant_domain = getattr(tenant, 'domain', None) if tenant else None
        slug = getattr(tenant, 'slug', None) or (getattr(tenant, 'id', None) if tenant else None)

        if tenant and tenant_domain:
            return f"/devices/{self.device_id}/login/"

        if slug:
            return f"/pos/tenants/{slug}/devices/{self.device_id}/login/"

        return f"/pos/devices/{self.device_id}/login/"


# Signal: ensure `public_url` is populated after save (post_save so PK exists)
@receiver(post_save, sender=POSDevice)
def posdevice_set_public_url(sender, instance, created, **kwargs):
    tenant = getattr(instance.branch, 'tenant', None)
    tenant_domain = getattr(tenant, 'domain', None) if tenant else None

    # Build path from `get_absolute_url()` (always returns a path)
    path = instance.get_absolute_url() or ''

    public = None
    site_url = getattr(settings, 'SITE_URL', '') or ''

    if tenant_domain:
        # tenant_domain may include scheme; prefer it if present
        if tenant_domain.startswith('http://') or tenant_domain.startswith('https://'):
            base = tenant_domain.rstrip('/')
        else:
            # default to https when only domain is provided
            base = f"https://{tenant_domain}".rstrip('/')
        public = base + path if path.startswith('/') else base + '/' + path
    elif site_url:
        base = site_url.rstrip('/')
        public = base + path if path.startswith('/') else base + '/' + path
    else:
        # No host available — keep path-only URL
        public = path

    # Normalize duplicate slashes but keep protocol intact
    public = public.replace('://', 'PROTOCOL_TEMP')
    while '//' in public:
        public = public.replace('//', '/')
    public = public.replace('PROTOCOL_TEMP', '://')

    # Persist only if changed to avoid recursion
    if (instance.public_url or '') != public:
        sender.objects.filter(pk=instance.pk).update(public_url=public)
