from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """Product category for menu organization"""

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='categories',
        db_index=True
    )

    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='categories',
        db_index=True,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0, db_index=True)
    icon = models.CharField(max_length=50, blank=True)

    # POS devices this category is available on
    pos_devices = models.ManyToManyField(
        'pos.POSDevice',
        related_name='categories',
        blank=True,
        help_text="POS devices where this category is available. Leave blank to make available on all devices in the branch."
    )

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        ordering = ['display_order', 'name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = [['tenant', 'branch', 'name']]
        indexes = [
            models.Index(fields=['tenant', 'branch', 'is_active', 'display_order']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Menu item/product"""

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='products',
        db_index=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        db_index=True
    )

    name = models.CharField(max_length=255, db_index=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)

    # POS devices this product is available on
    pos_devices = models.ManyToManyField(
        'pos.POSDevice',
        related_name='products',
        blank=True,
        help_text="POS devices where this product is available. Leave blank to make available on all devices in the branch."
    )

    # Pricing with Django 5.2 validators
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Selling price"
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost to make/buy"
    )

    # Image with organized upload path
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        null=True,
        blank=True,
        help_text="Product image"
    )

    # Availability flags
    is_available = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    track_inventory = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['tenant', 'is_active', 'is_available']),
            models.Index(fields=['category', 'is_available']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['sku'], name='unique_sku')
        ]

    def __str__(self):
        return self.name

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price and self.cost_price > 0:
            return round(((self.price - self.cost_price) / self.price) * 100, 2)
        return None