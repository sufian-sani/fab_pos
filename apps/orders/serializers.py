from rest_framework import serializers
from .models import Order, OrderItem, Payment
from django.utils import timezone


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'quantity',
            'unit_price',
            'total',
            'notes'
        ]
        read_only_fields = ['id', 'product_name', 'product_sku', 'total']


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_method',
            'amount',
            'reference',
            'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Complete order serializer"""
    
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    pos_device_name = serializers.CharField(source='pos_device.name', read_only=True)
    cashier_name = serializers.CharField(source='cashier.get_full_name', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'branch',
            'branch_name',
            'pos_device',
            'pos_device_name',
            'cashier',
            'cashier_name',
            'customer_name',
            'customer_phone',
            'subtotal',
            'tax',
            'discount',
            'total',
            'status',
            'payment_status',
            'notes',
            'items',
            'payments',
            'created_at',
            'updated_at',
            'completed_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'total',
            'created_at', 'updated_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    
    branch = serializers.IntegerField()
    pos_device = serializers.IntegerField()
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemSerializer(many=True)
    payments = PaymentSerializer(many=True)
    tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payments_data = validated_data.pop('payments')
        
        # Create order
        order = Order.objects.create(
            **validated_data,
            cashier=self.context['request'].user
        )
        
        # Create items
        for item_data in items_data:
            product = item_data.pop('product')
            OrderItem.objects.create(
                order=order,
                product=product,
                unit_price=product.price,
                **item_data
            )
        
        # Create payments
        for payment_data in payments_data:
            Payment.objects.create(order=order, **payment_data)
        
        # Calculate totals
        order.calculate_total()
        
        # Update payment status
        total_paid = sum(p.amount for p in order.payments.all())
        if total_paid >= order.total:
            order.payment_status = 'paid'
            order.status = 'completed'
            order.completed_at = timezone.now()
        elif total_paid > 0:
            order.payment_status = 'partial'
        
        order.save()
        
        return order
