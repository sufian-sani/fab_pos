from django.db import models


class Tenant(models.Model):
    """Restaurant company/owner - Multi-tenant base"""

    PLAN_CHOICES = [
        ('basic', 'Basic - 1 branch, 2 devices'),
        ('professional', 'Professional - 5 branches, 10 devices'),
        ('enterprise', 'Enterprise - Unlimited'),
    ]

    name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)

    subscription_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='basic',
        db_index=True
    )

    max_branches = models.IntegerField(default=1)
    max_devices = models.IntegerField(default=2)

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_at']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        indexes = [
            models.Index(fields=['email', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def can_add_branch(self):
        """Check if tenant can add more branches"""
        if self.max_branches == -1:  # Unlimited
            return True
        return self.branches.count() < self.max_branches