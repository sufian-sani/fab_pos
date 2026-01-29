from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Inventory(models.Model):
    """Stock level tracking per product per branch"""

    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='inventory',
        db_index=True
    )

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='inventory',
        db_index=True
    )

    quantity = models.IntegerField(default=0)
    minimum_quantity = models.IntegerField(default=10)
    maximum_quantity = models.IntegerField(default=100)

    last_restocked = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory'
        unique_together = ['branch', 'product']
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'
        indexes = [
            models.Index(fields=['branch', 'product']),
            models.Index(fields=['quantity']),
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.product.name}: {self.quantity}"

    def clean(self):
        """Validate inventory data"""
        if self.minimum_quantity > self.maximum_quantity:
            raise ValidationError('Minimum quantity cannot be greater than maximum quantity')

    @property
    def is_low_stock(self):
        """Check if stock is below minimum threshold"""
        return self.quantity <= self.minimum_quantity

    @property
    def is_out_of_stock(self):
        """Check if completely out of stock"""
        return self.quantity <= 0

    @property
    def stock_status(self):
        """Get human-readable stock status"""
        if self.is_out_of_stock:
            return 'OUT_OF_STOCK'
        elif self.is_low_stock:
            return 'LOW_STOCK'
        return 'IN_STOCK'

    def add_stock(self, quantity):
        """Add stock to inventory"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        self.quantity += quantity
        self.last_restocked = timezone.now()
        self.save(update_fields=['quantity', 'last_restocked', 'updated_at'])

    def remove_stock(self, quantity):
        """Remove stock from inventory"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if quantity > self.quantity:
            raise ValueError(f"Cannot remove {quantity} items. Only {self.quantity} available.")

        self.quantity -= quantity
        self.save(update_fields=['quantity', 'updated_at'])