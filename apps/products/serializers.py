from rest_framework import serializers
from .models import Category, Product
from django.contrib.auth import get_user_model

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category"""
    
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'branch',
            'branch_name',
            'name',
            'description',
            'display_order',
            'icon',
            'pos_devices',
            'is_active',
            'product_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_product_count(self, obj):
        """Count active products in this category"""
        return obj.products.filter(is_active=True).count()
    
    def validate_tenant(self, value):
        """Validate tenant based on user role"""
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        # Platform owner can set any tenant
        if request.user.is_platform_owner:
            return value
        
        # Tenant admin can only create for their tenant
        if request.user.is_tenant_admin:
            if value.id != request.user.tenant_id:
                raise serializers.ValidationError(
                    "You can only create categories for your own tenant"
                )
            return value
        
        raise serializers.ValidationError(
            "You don't have permission to create categories"
        )


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing categories"""
    
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'display_order', 'is_active', 'product_count']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product"""
    
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'category',
            'category_name',
            'name',
            'sku',
            'description',
            'price',
            'cost_price',
            'image',
            'pos_devices',
            'is_available',
            'is_active',
            'track_inventory',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_tenant(self, value):
        """Validate tenant based on user role"""
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        # Platform owner can set any tenant
        if request.user.is_platform_owner:
            return value
        
        # Tenant admin can only create for their tenant
        if request.user.is_tenant_admin:
            if value.id != request.user.tenant_id:
                raise serializers.ValidationError(
                    "You can only create products for your own tenant"
                )
            return value
        
        raise serializers.ValidationError(
            "You don't have permission to create products"
        )
    
    def validate_category(self, value):
        """Ensure category belongs to same tenant as product"""
        request = self.context.get('request')
        tenant = self.initial_data.get('tenant')
        
        if value and tenant:
            if value.tenant_id != int(tenant):
                raise serializers.ValidationError(
                    "Category must belong to the same tenant as the product"
                )
        
        return value
    
    def validate_sku(self, value):
        """Ensure SKU is unique"""
        instance = self.instance
        if Product.objects.filter(sku=value).exclude(
            id=instance.id if instance else None
        ).exists():
            raise serializers.ValidationError("Product with this SKU already exists")
        return value


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for POS and listing"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'category_name',
            'price',
            'image',
            'is_available'
        ]


class ProductPOSSerializer(serializers.ModelSerializer):
    """Minimal serializer for POS interface"""
    
    category = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price', 'category', 'image', 'is_available']
