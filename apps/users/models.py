from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based access
    
    Roles:
    - platform_owner: You (manages everything)
    - tenant_admin: Restaurant owner (manages their restaurant)
    - branch_manager: Manager (manages one branch)
    - cashier: POS user (uses POS only)
    """
    
    ROLE_CHOICES = [
        ('platform_owner', 'Platform Owner'),     # You - Super Admin
        ('tenant_admin', 'Tenant Admin'),         # Restaurant Owner
        ('branch_manager', 'Branch Manager'),     # Branch Manager
        ('cashier', 'Cashier'),                   # POS User
    ]
    
    # Basic Info
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    
    # Role & Permissions
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    
    # Tenant Relationship (null for platform owner)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        help_text="Which restaurant this user belongs to"
    )
    
    # Branch Relationship (null for tenant admins)
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
        help_text="Which branch this user manages/works at"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Use email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_platform_owner(self):
        """Check if user is platform owner (you)"""
        return self.role == 'platform_owner'
    
    @property
    def is_tenant_admin(self):
        """Check if user is restaurant owner"""
        return self.role == 'tenant_admin'
    
    @property
    def is_branch_manager(self):
        """Check if user is branch manager"""
        return self.role == 'branch_manager'
    
    @property
    def is_cashier(self):
        """Check if user is cashier"""
        return self.role == 'cashier'
    
    def can_manage_tenant(self, tenant):
        """Check if user can manage this tenant"""
        if self.is_platform_owner:
            return True  # Platform owner manages all
        if self.is_tenant_admin and self.tenant_id == tenant.id:
            return True  # Tenant admin manages their own
        return False
    
    def can_manage_branch(self, branch):
        """Check if user can manage this branch"""
        if self.is_platform_owner:
            return True  # Platform owner manages all
        if self.is_tenant_admin and self.tenant_id == branch.tenant_id:
            return True  # Tenant admin manages their branches
        if self.is_branch_manager and self.branch_id == branch.id:
            return True  # Branch manager manages their branch
        return False