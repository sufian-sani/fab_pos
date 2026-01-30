from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Sum, Count

from .models import Order, OrderItem, Payment
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderItemSerializer,
    PaymentSerializer
)


# ============================================================================
# ORDER VIEWSET
# ============================================================================

class OrderViewSet(viewsets.ModelViewSet):
    """
    Order management
    
    Endpoints:
    - GET /api/orders/ - List orders
    - POST /api/orders/ - Create order
    - GET /api/orders/{id}/ - Get order
    - PUT/PATCH /api/orders/{id}/ - Update order
    - DELETE /api/orders/{id}/ - Cancel order
    - POST /api/orders/{id}/complete/ - Complete order
    - POST /api/orders/{id}/cancel/ - Cancel order
    - POST /api/orders/{id}/refund/ - Refund order
    - POST /api/orders/{id}/add_payment/ - Add payment
    - GET /api/orders/today/ - Today's orders
    - GET /api/orders/statistics/ - Order statistics
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def get_queryset(self):
        """Filter orders based on user role"""
        user = self.request.user
        
        queryset = Order.objects.select_related(
            'branch',
            'branch__tenant',
            'pos_device',
            'cashier'
        ).prefetch_related(
            'items',
            'items__product',
            'payments'
        )
        
        if user.is_platform_owner:
            return queryset
        
        if user.is_tenant_admin:
            return queryset.filter(branch__tenant_id=user.tenant_id)
        
        if user.is_branch_staff:
            return queryset.filter(branch__staff=user)
        
        # Cashiers can only see their own orders
        return queryset.filter(cashier=user)
    
    def perform_create(self, serializer):
        """Create order with validation"""
        order = serializer.save()
        return order
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark order as completed"""
        order = self.get_object()
        
        if order.status == 'completed':
            return Response(
                {'error': 'Order already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order"""
        order = self.get_object()
        
        if order.status == 'completed':
            return Response(
                {'error': 'Cannot cancel completed order'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Refund order"""
        order = self.get_object()
        
        if order.payment_status != 'paid':
            return Response(
                {'error': 'Can only refund paid orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'refunded'
        order.payment_status = 'refunded'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Add payment to order"""
        order = self.get_object()
        
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save(order=order)
            
            # Update payment status
            total_paid = sum(p.amount for p in order.payments.all())
            
            if total_paid >= order.total:
                order.payment_status = 'paid'
                order.status = 'completed'
                order.completed_at = timezone.now()
            elif total_paid > 0:
                order.payment_status = 'partial'
            
            order.save()
            
            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's orders"""
        today = timezone.now().date()
        orders = self.get_queryset().filter(
            created_at__date=today
        )
        
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get order statistics"""
        queryset = self.get_queryset()
        
        # Date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Calculate statistics
        stats = queryset.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total'),
            completed_orders=Count('id', filter=Q(status='completed')),
            cancelled_orders=Count('id', filter=Q(status='cancelled')),
            pending_orders=Count('id', filter=Q(status='pending')),
        )
        
        # Average order value
        if stats['total_orders'] and stats['total_revenue']:
            stats['average_order_value'] = stats['total_revenue'] / stats['total_orders']
        else:
            stats['average_order_value'] = 0
        
        # Payment status breakdown
        payment_stats = queryset.values('payment_status').annotate(
            count=Count('id'),
            total=Sum('total')
        )
        
        stats['payment_breakdown'] = list(payment_stats)
        
        return Response(stats)
    
    def list(self, request, *args, **kwargs):
        """List orders with filtering"""
        queryset = self.get_queryset()
        
        # Filters
        status_filter = request.query_params.get('status')
        payment_status = request.query_params.get('payment_status')
        branch = request.query_params.get('branch')
        pos_device = request.query_params.get('pos_device')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        if branch:
            queryset = queryset.filter(branch_id=branch)
        
        if pos_device:
            queryset = queryset.filter(pos_device_id=pos_device)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ============================================================================
# ORDER ITEM VIEWSET (Optional - for managing individual items)
# ============================================================================

class OrderItemViewSet(viewsets.ModelViewSet):
    """
    Order item management (optional - mainly for viewing)
    """
    
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = OrderItem.objects.select_related(
            'order',
            'order__branch',
            'product'
        )
        
        if user.is_platform_owner:
            return queryset
        
        if user.is_tenant_admin:
            return queryset.filter(order__branch__tenant_id=user.tenant_id)
        
        if user.is_branch_staff:
            return queryset.filter(order__branch__staff=user)
        
        return queryset.filter(order__cashier=user)


# ============================================================================
# PAYMENT VIEWSET (Optional - for viewing payments)
# ============================================================================

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Payment viewing (read-only)
    Payments are created through orders
    """
    
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = Payment.objects.select_related(
            'order',
            'order__branch'
        )
        
        if user.is_platform_owner:
            return queryset
        
        if user.is_tenant_admin:
            return queryset.filter(order__branch__tenant_id=user.tenant_id)
        
        if user.is_branch_staff:
            return queryset.filter(order__branch__staff=user)
        
        return queryset.filter(order__cashier=user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Payment summary by method"""
        queryset = self.get_queryset()
        
        # Date filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        summary = queryset.values('payment_method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')
        
        return Response(summary)
