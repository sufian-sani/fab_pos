# System Architecture Overview

## Complete User Role & Access Matrix

```
┌─────────────────────┬──────────────────────────────────────────────────────┐
│     USER ROLE       │              WHAT THEY CAN ACCESS                    │
├─────────────────────┼──────────────────────────────────────────────────────┤
│ Platform Owner      │ ✓ All tenants, branches, users, products             │
│ (SaaS Admin)        │ ✓ System configuration & statistics                   │
│                     │ ✗ Cannot login to POS portal                          │
│                     │ Uses: Admin Interface                                 │
├─────────────────────┼──────────────────────────────────────────────────────┤
│ Tenant Admin        │ ✓ Their restaurant's all branches                     │
│ (Restaurant Owner)  │ ✓ All products, categories, users in their tenant     │
│                     │ ✓ Assign products to specific POS devices             │
│                     │ ✓ Manage admins, managers, cashiers                   │
│                     │ ✗ Cannot login to POS portal                          │
│                     │ Uses: Admin Interface & REST API                      │
├─────────────────────┼──────────────────────────────────────────────────────┤
│ Branch Manager      │ ✓ Their branch's menu & POS devices                   │
│                     │ ✓ View products available at their branch             │
│                     │ ✓ Manage cashiers in their branch                     │
│                     │ ✓ See inventory for their location                    │
│                     │ ✗ Cannot create/modify products                       │
│                     │ Uses: POS Portal                                      │
├─────────────────────┼──────────────────────────────────────────────────────┤
│ Cashier (POS User)  │ ✓ ONLY assigned POS device(s)                         │
│                     │ ✓ Menu items available at their device                │
│                     │ ✓ Process transactions/orders                         │
│                     │ ✗ Cannot see other devices' menu                      │
│                     │ ✗ Cannot view/modify any settings                     │
│                     │ Uses: POS Terminal/Portal                             │
└─────────────────────┴──────────────────────────────────────────────────────┘
```

---

## Data Isolation Layers

```
Layer 1: TENANT ISOLATION
├─ Platform Owner → Sees all tenants
├─ Tenant Admin → Sees only their tenant
├─ Branch Manager → Filtered to their tenant
└─ Cashier → Filtered to their tenant

Layer 2: BRANCH ISOLATION
├─ Platform Owner → Sees all branches
├─ Tenant Admin → Sees all branches in their tenant
├─ Branch Manager → Sees only their branch
└─ Cashier → Filtered to their branch

Layer 3: POS DEVICE ISOLATION
├─ Platform Owner → Sees all devices
├─ Tenant Admin → Sees all devices in their tenant
├─ Branch Manager → Sees branch devices (or assigned ones)
└─ Cashier → ONLY sees assigned devices

Layer 4: PRODUCT/CATEGORY FILTERS
├─ If pos_devices is EMPTY → Available on ALL devices
├─ If pos_devices has values → Available ONLY on those devices
└─ Access enforced in API filtering logic
```

---

## API Call Flow for POS Terminal

```
POS Terminal Application
│
├─ POST /api/users/pos_login/
│  ├─ Input: email, password
│  ├─ Validation:
│  │  ├─ User exists & active ✓
│  │  ├─ Role is cashier or branch_manager ✓
│  │  ├─ Has assigned POS devices ✓
│  │  └─ Return: JWT token + accessible devices
│  │
│  └─ Response: {access_token, refresh_token, user, pos_devices}
│
├─ GET /api/pos/portal/ [MAIN ENDPOINT]
│  ├─ Authorization: Bearer <JWT>
│  ├─ Filtering Logic:
│  │  ├─ Get user's accessible devices
│  │  ├─ Filter categories:
│  │  │  └─ WHERE (pos_devices IS NULL OR pos_devices IN user_devices)
│  │  └─ Filter products:
│  │     └─ WHERE (pos_devices IS NULL OR pos_devices IN user_devices)
│  │
│  └─ Response: [
│       {category: {id, name, ...}, products: [{id, name, price, ...}]},
│       ...
│     ]
│
├─ GET /api/pos/portal/search/?q=butter
│  ├─ Query: products matching search term
│  ├─ Same filtering logic applied
│  └─ Response: [{id, name, sku, price, ...}]
│
└─ GET /api/pos/portal/devices/
   ├─ Return: User's assigned POS devices
   └─ Response: [{id, name, device_id, status, ...}]
```

---

## Data Model Relationships

```
Tenant (Restaurant)
│
├── Branches (Locations)
│   │
│   ├── Categories
│   │   ├─ name
│   │   ├─ branch (FK)
│   │   ├─ tenant (FK)
│   │   └─ pos_devices (M2M) ← Device Restriction
│   │
│   ├── Products
│   │   ├─ name
│   │   ├─ category (FK)
│   │   ├─ tenant (FK)
│   │   └─ pos_devices (M2M) ← Device Restriction
│   │
│   ├── POSDevices
│   │   ├─ name (e.g., "Counter 1")
│   │   ├─ device_id (e.g., "POS-001")
│   │   ├─ device_type (tablet, desktop, mobile)
│   │   ├─ branch (FK)
│   │   └─ operators (M2M reverse from User)
│   │
│   └── Users
│       ├─ role (cashier, branch_manager)
│       ├─ branch (FK)
│       ├─ tenant (FK)
│       └─ pos_devices (M2M) ← Assignment
│
└── Users (Tenant Admin, Branch Manager, Cashier)
    ├─ email
    ├─ role
    ├─ tenant (FK)
    ├─ branch (FK)
    └─ pos_devices (M2M)
```

---

## Request Filtering Pipeline

```
User makes request: GET /api/pos/portal/

Step 1: Authentication
   ├─ Check JWT token validity
   ├─ Extract user_id from token
   └─ Proceed if authenticated

Step 2: Authorization
   ├─ Check POSPortalPermission
   ├─ Only (cashier OR branch_manager) allowed
   ├─ Reject if platform_owner or tenant_admin
   └─ Proceed if authorized

Step 3: Get User's POS Devices
   ├─ If cashier:
   │  └─ devices = user.pos_devices.all()
   ├─ If branch_manager:
   │  ├─ If user.pos_devices exists:
   │  │  └─ devices = user.pos_devices.all()
   │  └─ Else:
   │     └─ devices = POSDevice.filter(branch=user.branch)
   └─ Result: QuerySet of accessible devices

Step 4: Filter Categories
   ├─ Base filter:
   │  └─ Category.filter(
   │       tenant=user.tenant,
   │       branch=user.branch,
   │       is_active=True
   │     )
   ├─ Device filter:
   │  └─ .filter(
   │       Q(pos_devices__in=devices) |  ← Device assigned
   │       Q(pos_devices__isnull=True)   ← No restriction
   │     )
   └─ Result: Only accessible categories

Step 5: Filter Products
   ├─ Base filter:
   │  └─ Product.filter(
   │       tenant=user.tenant,
   │       is_active=True,
   │       is_available=True
   │     )
   ├─ Device filter:
   │  └─ .filter(
   │       Q(pos_devices__in=devices) |  ← Device assigned
   │       Q(pos_devices__isnull=True)   ← No restriction
   │     )
   └─ Result: Only accessible products

Step 6: Serialize & Return
   ├─ Combine categories + products
   ├─ Serialize using POSSerializer (minimal data)
   └─ Return JSON response
```

---

## Example: Two Counters, Different Menus

```
RESTAURANT: "Burger Place"
├─ Branch: "Main Street"
│
├─ POS DEVICE 1: "Counter 1" (Dine-In)
│  └─ Operators: [Cashier John]
│
├─ POS DEVICE 2: "Counter 2" (Drive-Thru)
│  └─ Operators: [Cashier Jane]
│
├─ CATEGORY 1: "Burgers"
│  └─ pos_devices: [] (available everywhere)
│
├─ CATEGORY 2: "Alcohol"
│  └─ pos_devices: [Counter 1 only] (age-restricted)
│
├─ PRODUCT 1: "Cheeseburger"
│  ├─ category: Burgers
│  └─ pos_devices: [] (available everywhere)
│
├─ PRODUCT 2: "Beer"
│  ├─ category: Alcohol
│  └─ pos_devices: [Counter 1 only]
│
└─ PRODUCT 3: "Milkshake"
   ├─ category: Drinks
   └─ pos_devices: [] (available everywhere)


CASHIER JOHN's MENU (Counter 1):
┌─────────────────┐
│ Burgers         │
│ - Cheeseburger  │  ← pos_devices=[] accessible
│                 │
│ Alcohol         │
│ - Beer          │  ← pos_devices=[Counter1] accessible
│                 │
│ Drinks          │
│ - Milkshake     │  ← pos_devices=[] accessible
└─────────────────┘


CASHIER JANE's MENU (Counter 2):
┌─────────────────┐
│ Burgers         │
│ - Cheeseburger  │  ← pos_devices=[] accessible
│                 │
│ Drinks          │
│ - Milkshake     │  ← pos_devices=[] accessible
│                 │
│ (Alcohol hidden)│  ← pos_devices=[Counter1] NOT accessible
└─────────────────┘
```

---

## Security Mechanisms

```
Defense Layer 1: Role-Based Access Control (RBAC)
├─ POSPortalPermission class
├─ Checks: user.is_cashier OR user.is_branch_manager
├─ Rejects: platform_owner, tenant_admin, anonymous users
└─ Result: Only authorized roles can access

Defense Layer 2: Tenant Isolation
├─ All queries filtered by user.tenant
├─ Prevents cross-tenant data leakage
├─ Applied at model level & API level
└─ Result: Users cannot see other restaurants' data

Defense Layer 3: Branch Isolation
├─ Categories filtered by user.branch
├─ Products filtered by user.tenant (cross-branch within tenant)
├─ Applied at QuerySet level
└─ Result: Users cannot see other locations' restricted items

Defense Layer 4: Device-Level Granularity
├─ POS device assignment per user
├─ Product/Category restricted per device
├─ Applied at filtering logic
└─ Result: Cashiers cannot see restricted menus/items

Defense Layer 5: Status Checks
├─ user.is_active must be True
├─ branch.is_active must be True (implied)
├─ pos_device.is_active must be True
├─ product.is_active & is_available must be True
└─ Result: Disabled items not accessible

Defense Layer 6: JWT Authentication
├─ Token-based stateless auth
├─ Token expiration (configured in settings)
├─ Token refresh mechanism
└─ Result: Secure request validation
```

---

## Performance Optimizations

```
1. QuerySet Optimization
   ├─ select_related() for ForeignKey lookups
   │  └─ reduces N+1 queries for tenant, branch
   ├─ prefetch_related() for ManyToMany
   │  └─ reduces N+1 queries for pos_devices
   └─ .distinct() for M2M queries
      └─ removes duplicate rows

2. Database Indexes
   ├─ On Category: (tenant, branch, is_active, display_order)
   ├─ On Product: (tenant, is_active, is_available)
   └─ On POSDevice: (branch, is_active)

3. Caching Opportunities
   ├─ Menu per device (relatively static)
   ├─ Category hierarchy (rarely changes)
   └─ Product availability (can be cached per device)

4. Serializer Optimization
   ├─ POSPortalSerializer uses minimal fields
   ├─ ProductPOSSerializer has fewer fields than ProductSerializer
   └─ Reduces payload size & transmission time
```

---

## Files Modified/Created

```
MODIFIED:
├─ apps/users/models.py
│  └─ Added: pos_devices ManyToManyField
├─ apps/users/views.py
│  └─ Added: pos_login() action
├─ apps/products/models.py
│  ├─ Added: branch field to Category
│  └─ Added: pos_devices M2M to both Category & Product
├─ apps/products/serializers.py
│  └─ Updated: CategorySerializer, ProductSerializer
├─ apps/pos/serializers.py
│  └─ Added: POSPortalDeviceSerializer
├─ apps/pos/urls.py
│  └─ Added: POSPortalMenuViewSet routes

CREATED:
├─ apps/pos/portal_views.py
│  └─ POSPortalMenuViewSet with filtering logic
├─ POS_PORTAL_DESIGN.md
│  └─ Complete system architecture documentation
├─ POS_PORTAL_QUICK_START.md
│  └─ Implementation guide with examples

MIGRATIONS:
├─ apps/products/migrations/0002_*.py
│  └─ Branch field & pos_devices M2M for Product & Category
├─ apps/users/migrations/0002_*.py
│  └─ pos_devices M2M for User
└─ apps/pos/migrations/0002_*.py (if needed)
   └─ Any POS model updates
```

