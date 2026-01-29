from django.db import models


class Branch(models.Model):
    """Physical restaurant location"""

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='branches',
        db_index=True
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, db_index=True)

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)

    # Contact
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    # Operating hours
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'branches'
        ordering = ['tenant', 'name']
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['city']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"