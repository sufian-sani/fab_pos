from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from .models import User
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserProfileSerializer,
    LoginSerializer,
    MyTokenObtainPairSerializer
)
from .permissions import (
    IsPlatformOwner,
    IsTenantAdminOrAbove,
    IsBranchManagerOrAbove,
    CanManageUser
)


class UserViewSet(viewsets.ModelViewSet, MyTokenObtainPairSerializer):
    """
    ViewSet for User management
    
    Endpoints:
    - GET /api/users/ - List users (filtered by role)
    - POST /api/users/ - Create new user
    - GET /api/users/{id}/ - Get user details
    - PUT /api/users/{id}/ - Update user
    - DELETE /api/users/{id}/ - Delete user
    - POST /api/users/login/ - Login
    - GET /api/users/me/ - Get current user profile
    - PUT /api/users/me/update/ - Update own profile
    - POST /api/users/change_password/ - Change password
    - GET /api/users/by_role/ - Get users by role
    """
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'tenant', 'branch']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email', 'role']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """Filter users based on user's role"""
        user = self.request.user
        
        # Platform owner sees all users
        if user.is_platform_owner:
            return self.queryset
        
        # Tenant admin sees users in their tenant
        if user.is_tenant_admin:
            return self.queryset.filter(tenant=user.tenant)
        
        # Branch manager sees cashiers in their branch
        if user.is_branch_manager:
            return self.queryset.filter(
                role='cashier',
                branch=user.branch
            )
        
        # Cashiers see only themselves
        return self.queryset.filter(id=user.id)
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        if self.action == 'me':
            return UserProfileSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'login':
            return [AllowAny()]
        if self.action == 'create':
            return [IsBranchManagerOrAbove()]
        return [IsAuthenticated(), CanManageUser()]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        User login endpoint
        
        POST /api/users/login/
        Body: {"email": "user@example.com", "password": "password"}
        
        Returns: JWT tokens + user info
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(email=email, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

         # ✅ Add custom claims (user info inside JWT)
        refresh['id'] = user.id
        refresh['email'] = user.email
        refresh['username'] = user.username

        # breakpoint()

        # # if you have role field
        if hasattr(user, 'role'):
            refresh['role'] = user.role

        # # if you have tenant
        if hasattr(user, 'tenant') and user.tenant:
            refresh['tenant'] = user.tenant.id

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data
        })
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user profile
        
        GET /api/users/me/
        """
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        Update current user profile
        
        PUT /api/users/update_profile/
        """
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Change user password
        
        POST /api/users/change_password/
        Body: {
            "old_password": "old",
            "new_password": "new",
            "new_password_confirm": "new"
        }
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'})
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """
        Get users by role
        
        GET /api/users/by_role/?role=cashier
        """
        role = request.query_params.get('role')
        
        if not role:
            return Response(
                {'error': 'Role parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = self.get_queryset().filter(role=role)
        serializer = self.get_serializer(users, many=True)
        
        return Response({
            'role': role,
            'count': users.count(),
            'users': serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsTenantAdminOrAbove])
    def activate(self, request, pk=None):
        """
        Activate user account
        
        POST /api/users/{id}/activate/
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response({
            'message': f'User {user.email} activated',
            'user': UserSerializer(user).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsTenantAdminOrAbove])
    def deactivate(self, request, pk=None):
        """
        Deactivate user account
        
        POST /api/users/{id}/deactivate/
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response({
            'message': f'User {user.email} deactivated',
            'user': UserSerializer(user).data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get user statistics
        
        GET /api/users/stats/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_users': queryset.count(),
            'active_users': queryset.filter(is_active=True).count(),
            'by_role': {}
        }
        
        # Count by role
        for role_code, role_name in User.ROLE_CHOICES:
            stats['by_role'][role_code] = {
                'name': role_name,
                'count': queryset.filter(role=role_code).count()
            }
        
        return Response(stats)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def pos_login(self, request):
        """
        POS Portal Login - Special endpoint for POS terminals
        
        This endpoint is used by POS terminals (cashiers/branch managers)
        to authenticate and get their accessible menu.
        
        POST /api/users/pos_login/
        Body: {"email": "cashier@example.com", "password": "password", "device_id": "POS-001"}
        
        Returns:
        - JWT tokens
        - User info
        - List of accessible POS devices
        - Menu preview (categories + products available for this user)
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(email=email, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has POS access
        if user.is_platform_owner or user.is_tenant_admin:
            return Response(
                {'error': 'This user cannot access POS portal. Use admin interface instead.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has assigned POS devices
        if user.is_cashier and not user.pos_devices.exists():
            return Response(
                {'error': 'No POS devices assigned to this user'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user.is_branch_manager and not user.branch:
            return Response(
                {'error': 'Branch not assigned to this user'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Get accessible POS devices
        if user.is_cashier:
            accessible_devices = user.pos_devices.filter(is_active=True)
        else:  # branch_manager
            if user.pos_devices.exists():
                accessible_devices = user.pos_devices.filter(is_active=True)
            else:
                from apps.pos.models import POSDevice
                accessible_devices = POSDevice.objects.filter(
                    branch=user.branch,
                    is_active=True
                )
        
        if not accessible_devices.exists():
            return Response(
                {'error': 'No active POS devices available for this user'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from apps.pos.serializers import POSPortalDeviceSerializer
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data,
            'pos_devices': POSPortalDeviceSerializer(
                accessible_devices,
                many=True
            ).data,
            'device_count': accessible_devices.count(),
            'message': f'Successfully authenticated. {accessible_devices.count()} POS device(s) available.'
        })
