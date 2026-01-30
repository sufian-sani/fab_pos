from django.db import models
from django.utils import timezone
import uuid

class Device(models.Model):
    """
    POS Device/Terminal
    Each device belongs to a branch
    """
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('suspended', 'Suspended'),
    ]
    
    DEVICE_TYPE_CHOICES = [
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop POS'),
        ('mobile', 'Mobile'),
        ('kiosk', 'Self-Service Kiosk'),
    ]
    
    # Relationship
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='pos_devices'
    )
    
    # Device assigned to specific user (cashier)
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        related_name='assigned_devices',
        null=True,
        blank=True,
        limit_choices_to={'role': 'cashier'}
    )
    
    # Device Info
    name = models.CharField(
        max_length=255,
        help_text="Device name (e.g., Counter 1, Drive-thru)"
    )
    
    device_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique device identifier"
    )
    
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        default='tablet'
    )
    
    # Hardware Info
    serial_number = models.CharField(
        max_length=255,
        blank=True,
        help_text="Device serial number"
    )
    
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        help_text="MAC address"
    )
    
    model = models.CharField(
        max_length=255,
        blank=True,
        help_text="Device model (e.g., iPad Pro, Samsung Tab)"
    )
    
    # Authentication
    auth_token = models.CharField(
        max_length=255,
        unique=True,
        default=uuid.uuid4,
        help_text="Device authentication token"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )
    
    is_active = models.BooleanField(default=True)
    
    # Connection Info
    last_online = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Software Info
    os_version = models.CharField(max_length=100, blank=True)
    app_version = models.CharField(max_length=50, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pos_devices'
        verbose_name = 'POS Device'
        verbose_name_plural = 'POS Devices'
        ordering = ['branch', 'name']
        indexes = [
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['device_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.branch.name})"
    
    @property
    def is_online(self):
        """Check if device is currently online (last seen < 5 minutes ago)"""
        if not self.last_online:
            return False
        
        threshold = timezone.now() - timezone.timedelta(minutes=5)
        return self.last_online > threshold
    
    @property
    def tenant(self):
        """Get tenant through branch"""
        return self.branch.tenant
    
    def update_online_status(self, ip_address=None):
        """Update device online status"""
        self.last_online = timezone.now()
        self.status = 'active'
        if ip_address:
            self.ip_address = ip_address
        self.save(update_fields=['last_online', 'status', 'ip_address', 'updated_at'])


class DeviceLog(models.Model):
    """
    Device activity log
    Track device actions and events
    """
    
    LOG_TYPE_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('online', 'Device Online'),
        ('offline', 'Device Offline'),
        ('error', 'Error'),
        ('sale', 'Sale Transaction'),
        ('sync', 'Data Sync'),
    ]
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    message = models.TextField()
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'device_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.log_type} - {self.created_at}"
