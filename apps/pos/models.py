from django.db import models
from django.utils import timezone


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
    
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='devices'
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
        return f"{self.branch.name} - {self.name}"
    
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
