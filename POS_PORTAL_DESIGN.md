# POS Portal Access Control System Design

## Overview

This document describes the multi-role, multi-tenant POS portal system that enables different user types to access only the products, categories, and menus relevant to them.

---

## User Roles & Hierarchy

```
Platform Owner (You - SaaS Admin)
├── Can access all tenants, branches, and POS devices
├── Uses: Admin Interface & REST API
└── Cannot access: POS Portal

Tenant Admin (Restaurant Owner)
├── Can access all branches and POS devices within their tenant
├── Uses: Admin Interface & REST API
├── Can create/manage: Users, branches, products, categories, POS devices
└── Cannot access: POS Portal

Branch Manager
├── Can access: Their assigned branch and its POS devices (or specific devices)
├── Uses: POS Portal or Mobile App
├── Can manage: Cashiers in their branch
├── Limited access to: Products, categories, inventory

Cashier (POS User)
├── Can access: Only assigned POS device(s)
├── Uses: POS Portal/Terminal only
├── Permissions: View menu, create orders
└── Access level: Most restricted
```

---

## Data Flow Architecture

```
┌─────────────────┐
│   POS Terminal  │
└────────┬────────┘
         │
         │ 1. pos_login (email + password)
         ▼
┌────────────────────────┐
│ /api/users/pos_login/  │ ◄── POST with credentials
└────────┬───────────────┘
         │
         │ 2. Returns:
         │    - JWT Tokens
         │    - User Info
         │    - Accessible POS Devices
         │
         ▼
┌────────────────────────────┐
│  Store JWT & Device ID     │
└────────┬───────────────────┘
         │
         │ 3. GET /api/pos/portal/
         │    (with Authorization header)
         │
         ▼
┌────────────────────────────────┐
│ POSPortalMenuViewSet.menu()    │
│                                │
│ 1. Get user's accessible       │
│    POS devices                 │
│ 2. Filter categories:          │
│    - Assigned to user's device │
│    - OR available to all       │
│ 3. Filter products:            │
│    - Assigned to user's device │
│    - OR available to all       │
│ 4. Return structured menu      │
│    (categories + products)     │
└────────┬───────────────────────┘
         │
         ▼
    Display Menu
    on POS Terminal
```

---

## Key Design Components

### 1. User Model Enhancement

**New Field:**
```python
pos_devices = models.ManyToManyField(
    'pos.POSDevice',
    related_name='operators',
    blank=True
)
```

**Usage:**
- **Cashier:** Must have 1+ POS devices assigned
- **Branch Manager:** Can have specific devices (optional) or all in branch
- **Tenant Admin:** No assignment (uses admin interface)
- **Platform Owner:** No assignment (uses admin interface)

### 2. Category & Product Scoping

**Category Model:**
- `tenant` - Which restaurant (multi-tenant isolation)
- `branch` - Which physical location
- `pos_devices` (ManyToMany) - Which POS terminals it appears on
  - If empty → Available on ALL devices in the branch
  - If populated → Available ONLY on specified devices

**Product Model:**
- `tenant` - Which restaurant
- `pos_devices` (ManyToMany) - Which POS terminals it appears on
  - If empty → Available on ALL devices in the tenant
  - If populated → Available ONLY on specified devices

### 3. Access Control Filtering

**Filtering Logic for User's Accessible Data:**

```python
def get_user_pos_devices():
    if user.is_cashier:
        # See only assigned devices
        return user.pos_devices.filter(is_active=True)
    
    if user.is_branch_manager:
        if user.pos_devices.exists():
            # If specific devices assigned
            return user.pos_devices.filter(is_active=True)
        else:
            # Otherwise, all devices in their branch
            return POSDevice.objects.filter(
                branch=user.branch,
                is_active=True
            )
```

**Category/Product Filtering:**

```python
categories = Category.objects.filter(
    tenant=user.tenant,
    branch=user.branch,
    is_active=True
).filter(
    # Either explicitly assigned to user's devices
    # OR available to all (no device restrictions)
    Q(pos_devices__in=user_devices) | 
    Q(pos_devices__isnull=True)
).distinct()
```

---

## API Endpoints

### Authentication

#### POST `/api/users/pos_login/`
**Purpose:** POS Terminal Login  
**Access:** Anonymous (AllowAny)  
**Request:**
```json
{
    "email": "cashier@restaurant.com",
    "password": "password123",
    "device_id": "POS-001"  // Optional
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
        "id": 1,
        "email": "cashier@restaurant.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "cashier",
        "branch": 1,
        "tenant": 1
    },
    "pos_devices": [
        {
            "id": 1,
            "name": "Counter 1",
            "device_id": "POS-001",
            "device_type": "tablet",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        }
    ],
    "device_count": 1,
    "message": "Successfully authenticated. 1 POS device(s) available."
}
```

**Error Cases:**
- Invalid credentials → 401 Unauthorized
- Account disabled → 403 Forbidden
- User is platform owner/tenant admin → 403 Forbidden (use admin interface)
- No POS devices assigned → 403 Forbidden
- No active POS devices → 403 Forbidden

---

### POS Portal Menu

**Base URL:** `/api/pos/portal/`  
**Permission:** POSPortalPermission (cashier or branch_manager only)

#### GET `/api/pos/portal/`
**Purpose:** Get complete menu for user's POS devices  
**Most Common Endpoint** - Returns categories with products organized by category

**Response:**
```json
{
    "devices_count": 2,
    "category_count": 3,
    "categories": [
        {
            "category": {
                "id": 1,
                "name": "Appetizers",
                "display_order": 1,
                "is_active": true,
                "product_count": 5
            },
            "products": [
                {
                    "id": 101,
                    "name": "Samosas",
                    "sku": "APP-001",
                    "price": "4.99",
                    "category": "Appetizers",
                    "image": "/media/products/samosa.jpg",
                    "is_available": true
                },
                {
                    "id": 102,
                    "name": "Spring Rolls",
                    "sku": "APP-002",
                    "price": "5.99",
                    "category": "Appetizers",
                    "image": "/media/products/spring_rolls.jpg",
                    "is_available": true
                }
            ],
            "product_count": 2
        }
    ]
}
```

#### GET `/api/pos/portal/categories/`
**Purpose:** Get only categories available for user's POS devices

**Response:**
```json
{
    "count": 3,
    "categories": [
        {
            "id": 1,
            "name": "Appetizers",
            "display_order": 1,
            "is_active": true,
            "product_count": 5
        }
    ]
}
```

#### GET `/api/pos/portal/products/`
**Purpose:** Get only products available for user's POS devices  
**Query Parameters:**
- `category_id` - Filter by category
- `device_id` - Filter by specific device (if user has multiple)

**Response:**
```json
{
    "count": 25,
    "products": [
        {
            "id": 101,
            "name": "Samosas",
            "sku": "APP-001",
            "price": "4.99",
            "category": "Appetizers",
            "image": "/media/products/samosa.jpg",
            "is_available": true
        }
    ]
}
```

#### GET `/api/pos/portal/devices/`
**Purpose:** Get list of POS devices accessible by user

**Response:**
```json
{
    "count": 2,
    "devices": [
        {
            "id": 1,
            "name": "Counter 1",
            "device_id": "POS-001",
            "device_type": "tablet",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        },
        {
            "id": 2,
            "name": "Counter 2",
            "device_id": "POS-002",
            "device_type": "desktop",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        }
    ]
}
```

#### GET `/api/pos/portal/search/?q=samosa`
**Purpose:** Search products by name or SKU

**Response:**
```json
{
    "query": "samosa",
    "count": 2,
    "products": [
        {
            "id": 101,
            "name": "Samosas",
            "sku": "APP-001",
            "price": "4.99",
            "category": "Appetizers",
            "image": "/media/products/samosa.jpg",
            "is_available": true
        },
        {
            "id": 102,
            "name": "Samosa Chat",
            "sku": "APP-003",
            "price": "6.99",
            "category": "Appetizers",
            "image": "/media/products/samosa_chat.jpg",
            "is_available": true
        }
    ]
}
```

---

## Usage Scenarios

### Scenario 1: Cashier at Counter 1
```
1. Logs in with: email=john@restaurant.com, password=***
2. System returns: 1 POS device assigned (Counter 1)
3. Calls GET /api/pos/portal/
4. Sees:
   - Categories assigned to Counter 1
   - OR Categories with no device restriction
   - Products assigned to Counter 1
   - OR Products with no device restriction
5. Cannot see products/categories assigned ONLY to Counter 2
```

### Scenario 2: Branch Manager with Multiple Devices
```
1. Logs in with: email=manager@restaurant.com, password=***
2. System returns: 2 POS devices (all devices in branch, no specific assignment)
3. Calls GET /api/pos/portal/
4. Sees: Products/categories available on ANY device in the branch
5. Can use /devices endpoint to list all branch devices
```

### Scenario 3: Tenant Admin
```
1. Attempts to login via pos_login
2. System returns: 403 Forbidden
   "This user cannot access POS portal. Use admin interface instead."
3. Must use regular /api/users/login/ → Admin Dashboard
```

---

## Security Features

### 1. Role-Based Access Control (RBAC)
- Users can only see data for their role level
- Tenant isolation enforced at model level
- Branch isolation enforced at filtering level

### 2. Device-Level Granularity
- Cashiers restricted to assigned devices
- Products/categories restricted per device
- Enables menu customization per location

### 3. Authentication
- JWT tokens for stateless API
- Separate POS login endpoint with validation
- Token refresh mechanism

### 4. Data Filtering
- Multiple filter layers:
  1. User role (platform_owner vs tenant_admin vs cashier)
  2. Tenant (which restaurant)
  3. Branch (which location)
  4. POS Device (which terminal)
  5. Active/Available status

### 5. Query Optimization
```python
# Prefetch related data to reduce N+1 queries
categories = Category.objects.filter(...).prefetch_related('pos_devices')
products = Product.objects.select_related('tenant', 'category')
```

---

## Configuration & Administration

### Setting Up a Cashier

1. Create user with role=`cashier`
2. Assign to `branch`
3. Add to `pos_devices` ManyToMany (1+ devices)
4. User logs in via POS terminal
5. Only sees menu for assigned devices

### Creating Branch-Specific Menu

1. Create `Category` with:
   - `tenant` = restaurant
   - `branch` = specific branch
   - `pos_devices` = leave empty (available on all devices in branch)
   
2. OR specify specific devices:
   - `pos_devices` = [Counter 1, Counter 2] (only these see it)

### Creating Device-Specific Products

1. Create `Product` with:
   - `tenant` = restaurant
   - `pos_devices` = leave empty (available everywhere)
   
2. OR restrict to specific devices:
   - `pos_devices` = [Counter 1] (only Counter 1 can sell this)

---

## Implementation Checklist

✅ User model enhanced with `pos_devices` ManyToMany field  
✅ POSPortalPermission class created  
✅ POSPortalMenuViewSet with filtering logic  
✅ POS login endpoint (`pos_login`) with validation  
✅ Multiple menu endpoints:
   - `menu/menu/` - Complete menu
   - `menu/categories/` - Categories only
   - `menu/products/` - Products only
   - `menu/devices/` - User's devices
   - `menu/search/` - Product search
✅ Serializers for POS portal (minimal data)  
✅ Database migration for pos_devices  
✅ URL routing configured  

---

## Future Enhancements

1. **Device Token Authentication**
   - Device-level auth tokens (in addition to user tokens)
   - Offline mode support for POS terminals

2. **Menu Variants**
   - Different menus for breakfast/lunch/dinner
   - Time-based menu availability

3. **Device-Specific Pricing**
   - Different prices for different devices/locations
   - Dynamic pricing rules

4. **Audit Logging**
   - Track what each cashier sees/orders
   - Login/logout tracking per device

5. **Advanced Filtering**
   - Dietary restrictions (vegan, gluten-free)
   - Allergen information
   - Prep time estimates
