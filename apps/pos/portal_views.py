"""
POS Portal Views

This module handles the POS portal where cashiers and branch managers
can access only the products, categories, and menus relevant to their
assigned POS devices.

The filtering logic ensures:
1. Cashiers see products/categories for their assigned POS devices only
2. Branch managers see products/categories for their branch's devices (or specific ones)
3. Access is scoped by POS device, tenant, and branch
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch

from apps.products.models import Category, Product
from apps.products.serializers import (
    CategoryListSerializer,
    ProductPOSSerializer,
    CategorySerializer
)
from apps.pos.models import POSDevice
from apps.pos.serializers import POSPortalDeviceSerializer


class POSPortalPermission(IsAuthenticated):
    """
    Permission check for POS Portal access.
    Only users with cashier, branch_manager roles and assigned POS devices can access.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # Platform owner and tenant admin access through regular admin views
        if request.user.is_platform_owner or request.user.is_tenant_admin:
            return False  # Use admin endpoints instead
        
        # Only cashier and branch manager roles can access POS portal
        return request.user.is_cashier or request.user.is_branch_manager


class POSPortalMenuViewSet(viewsets.ReadOnlyModelViewSet):
    """
    POS Portal - Get categories and products available for a specific POS device.
    
    This is the main endpoint for POS terminals. It returns only products and categories
    that are:
    1. Active and available
    2. Assigned to the user's POS device (or available on all devices in the branch)
    3. Within the user's tenant and branch
    
    Endpoints:
    - GET /api/pos/portal/ - Get complete menu for user's POS devices
    - GET /api/pos/portal/categories/ - Get categories only
    - GET /api/pos/portal/products/ - Get products only
    - GET /api/pos/portal/devices/ - Get user's accessible devices
    - GET /api/pos/portal/search/ - Search products
    """
    
    permission_classes = [POSPortalPermission]
    
    def get_user_pos_devices(self):
        """
        Get POS devices accessible by the current user.
        
        Returns:
        - For cashier: devices explicitly assigned to them
        - For branch_manager: all devices in their branch (or specific ones if assigned)
        - For branch staff: devices assigned to them
        """
        user = self.request.user
        
        if user.is_cashier:
            # Cashier sees only their assigned devices
            return user.pos_devices.filter(is_active=True)
        
        if user.is_branch_manager:
            # Branch manager sees all devices in their branch (or specific ones if assigned)
            if user.pos_devices.exists():
                # If specific devices assigned, show those
                return user.pos_devices.filter(is_active=True)
            else:
                # Otherwise show all devices in their branch
                return POSDevice.objects.filter(
                    branch=user.branch,
                    is_active=True
                )
        
        return POSDevice.objects.none()
    
    def list(self, request, *args, **kwargs):
        """
        Override list to return complete menu (categories with products).
        GET /api/pos/portal/
        """
        return self.menu(request)
    
    @action(detail=False, methods=['get'])
    def devices(self, request):
        """
        Get list of POS devices accessible by the user.
        
        GET /api/pos/portal/devices/
        """
        devices = self.get_user_pos_devices()
        serializer = POSPortalDeviceSerializer(devices, many=True)
        return Response({
            'count': devices.count(),
            'devices': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get categories available for user's POS devices.
        
        GET /api/pos/portal/categories/
        GET /api/pos/portal/categories/?device_id=1
        """
        user = self.request.user
        devices = self.get_user_pos_devices()
        
        if not devices.exists():
            return Response({
                'count': 0,
                'categories': []
            })
        
        # Get categories that are either:
        # 1. Explicitly assigned to the user's devices, OR
        # 2. Not assigned to any specific device (available on all devices)
        categories = Category.objects.filter(
            tenant=user.tenant,
            branch=user.branch,
            is_active=True
        ).filter(
            Q(pos_devices__in=devices) | Q(pos_devices__isnull=True)
        ).distinct().prefetch_related(
            Prefetch('pos_devices', queryset=devices)
        )
        
        serializer = CategoryListSerializer(categories, many=True)
        return Response({
            'count': categories.count(),
            'categories': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def products(self, request):
        """
        Get products available for user's POS devices.
        
        GET /api/pos/portal/products/
        GET /api/pos/portal/products/?category_id=1
        GET /api/pos/portal/products/?device_id=1
        """
        user = self.request.user
        devices = self.get_user_pos_devices()
        
        if not devices.exists():
            return Response({
                'count': 0,
                'products': []
            })
        
        # Get products that are either:
        # 1. Explicitly assigned to the user's devices, OR
        # 2. Not assigned to any specific device (available on all devices)
        products = Product.objects.filter(
            tenant=user.tenant,
            is_active=True,
            is_available=True
        ).filter(
            Q(pos_devices__in=devices) | Q(pos_devices__isnull=True)
        ).distinct()
        
        # Filter by category if provided
        category_id = request.query_params.get('category_id')
        if category_id:
            products = products.filter(category_id=category_id)
        
        serializer = ProductPOSSerializer(products, many=True)
        return Response({
            'count': products.count(),
            'products': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def menu(self, request):
        """
        Get complete menu (categories with products) for user's POS devices.
        This is the primary endpoint for POS terminals.
        
        GET /api/pos/portal/
        """
        user = self.request.user
        devices = self.get_user_pos_devices()
        
        if not devices.exists():
            return Response({
                'devices_count': 0,
                'categories': [],
                'message': 'No POS devices assigned to this user'
            })
        
        # Get accessible categories
        categories = Category.objects.filter(
            tenant=user.tenant,
            branch=user.branch,
            is_active=True
        ).filter(
            Q(pos_devices__in=devices) | Q(pos_devices__isnull=True)
        ).distinct().order_by('display_order', 'name')
        
        # Build menu structure
        menu = []
        for category in categories:
            # Get products in this category
            products = Product.objects.filter(
                category=category,
                tenant=user.tenant,
                is_active=True,
                is_available=True
            ).filter(
                Q(pos_devices__in=devices) | Q(pos_devices__isnull=True)
            ).distinct()
            
            menu.append({
                'category': CategoryListSerializer(category).data,
                'products': ProductPOSSerializer(products, many=True).data,
                'product_count': products.count()
            })
        
        return Response({
            'devices_count': devices.count(),
            'category_count': len(menu),
            'categories': menu
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search products by name or SKU in user's accessible menu.
        
        GET /api/pos/portal/search/?q=searchterm
        """
        user = self.request.user
        devices = self.get_user_pos_devices()
        query = request.query_params.get('q', '').strip()
        
        if not query or len(query) < 2:
            return Response({
                'query': query,
                'count': 0,
                'products': [],
                'message': 'Query must be at least 2 characters'
            })
        
        if not devices.exists():
            return Response({
                'query': query,
                'count': 0,
                'products': []
            })
        
        # Search products by name or SKU
        products = Product.objects.filter(
            tenant=user.tenant,
            is_active=True,
            is_available=True
        ).filter(
            Q(pos_devices__in=devices) | Q(pos_devices__isnull=True)
        ).filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        ).distinct()
        
        serializer = ProductPOSSerializer(products, many=True)
        return Response({
            'query': query,
            'count': products.count(),
            'products': serializer.data
        })

