from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    CategoryListSerializer,
    ProductSerializer,
    ProductListSerializer,
    ProductPOSSerializer
)
from .permissions import (
    CanCreateCategory,
    CanManageCategory,
    CanCreateProduct,
    CanManageProduct
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category management
    
    Permissions:
    - CREATE: platform_owner, tenant_admin only
    - READ: All authenticated users (filtered by tenant)
    - UPDATE: platform_owner, tenant_admin only
    - DELETE: platform_owner, tenant_admin only
    
    Endpoints:
    - GET /api/categories/ - List categories
    - POST /api/categories/ - Create category (admin only)
    - GET /api/categories/{id}/ - Get category details
    - PUT /api/categories/{id}/ - Update category (admin only)
    - DELETE /api/categories/{id}/ - Delete category (admin only)
    - GET /api/categories/active/ - Get active categories only
    - POST /api/categories/{id}/toggle_active/ - Toggle active status
    """
    
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, CanCreateCategory, CanManageCategory]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tenant', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['display_order', 'name', 'created_at']
    ordering = ['display_order', 'name']
    
    def get_queryset(self):
        """Filter categories based on user's role"""
        user = self.request.user
        
        # Platform owner sees all categories
        if user.is_platform_owner:
            return self.queryset
        
        # Tenant admin, branch manager, and cashiers see their tenant's categories
        if user.tenant:
            return self.queryset.filter(tenant=user.tenant)
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return CategoryListSerializer
        return CategorySerializer
    
    def perform_create(self, serializer):
        """Set tenant automatically for tenant admin"""
        user = self.request.user
        
        if user.is_tenant_admin:
            # Force tenant to user's tenant
            serializer.save(tenant=user.tenant)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get only active categories
        GET /api/categories/active/
        """
        categories = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        Toggle category active status
        POST /api/categories/{id}/toggle_active/
        """
        category = self.get_object()
        category.is_active = not category.is_active
        category.save()
        
        return Response({
            'message': f'Category {"activated" if category.is_active else "deactivated"}',
            'category': CategorySerializer(category).data
        })


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product management
    
    Permissions:
    - CREATE: platform_owner, tenant_admin only
    - READ: All authenticated users (filtered by tenant)
    - UPDATE: platform_owner, tenant_admin only
    - DELETE: platform_owner, tenant_admin only
    
    Endpoints:
    - GET /api/products/ - List products
    - POST /api/products/ - Create product (admin only)
    - GET /api/products/{id}/ - Get product details
    - PUT /api/products/{id}/ - Update product (admin only)
    - DELETE /api/products/{id}/ - Delete product (admin only)
    - GET /api/products/pos_menu/ - Get products for POS
    - GET /api/products/available/ - Get available products
    - GET /api/products/by_category/ - Get products by category
    - POST /api/products/{id}/toggle_available/ - Toggle availability
    """
    
    queryset = Product.objects.select_related('tenant', 'category')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, CanCreateProduct, CanManageProduct]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tenant', 'category', 'is_available', 'is_active', 'track_inventory']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter products based on user's role"""
        user = self.request.user
        
        # Platform owner sees all products
        if user.is_platform_owner:
            return self.queryset
        
        # Tenant admin, branch manager, and cashiers see their tenant's products
        if user.tenant:
            return self.queryset.filter(tenant=user.tenant)
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'list':
            return ProductListSerializer
        if self.action == 'pos_menu':
            return ProductPOSSerializer
        return ProductSerializer
    
    def perform_create(self, serializer):
        """Set tenant automatically for tenant admin"""
        user = self.request.user
        
        if user.is_tenant_admin:
            # Force tenant to user's tenant
            serializer.save(tenant=user.tenant)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def pos_menu(self, request):
        """
        Get products for POS interface
        Only available and active products
        
        GET /api/products/pos_menu/
        GET /api/products/pos_menu/?category=1
        """
        products = self.get_queryset().filter(
            is_active=True,
            is_available=True
        )
        
        # Filter by category if provided
        category_id = request.query_params.get('category')
        if category_id:
            products = products.filter(category_id=category_id)
        
        serializer = ProductPOSSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get only available products
        GET /api/products/available/
        """
        products = self.get_queryset().filter(is_available=True, is_active=True)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get products grouped by category
        GET /api/products/by_category/
        """
        categories = Category.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).prefetch_related('products')
        
        result = []
        for category in categories:
            products = category.products.filter(
                is_active=True,
                is_available=True
            )
            
            result.append({
                'category': CategorySerializer(category).data,
                'products': ProductPOSSerializer(products, many=True).data
            })
        
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def toggle_available(self, request, pk=None):
        """
        Toggle product availability
        POST /api/products/{id}/toggle_available/
        """
        product = self.get_object()
        product.is_available = not product.is_available
        product.save()
        
        return Response({
            'message': f'Product {"available" if product.is_available else "unavailable"}',
            'product': ProductSerializer(product).data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get product statistics
        GET /api/products/stats/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_products': queryset.count(),
            'active_products': queryset.filter(is_active=True).count(),
            'available_products': queryset.filter(is_available=True, is_active=True).count(),
            'by_category': []
        }
        
        # Products by category
        categories = Category.objects.filter(
            tenant=request.user.tenant
        ).annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        )
        
        for category in categories:
            stats['by_category'].append({
                'category': category.name,
                'count': category.product_count
            })
        
        return Response(stats)