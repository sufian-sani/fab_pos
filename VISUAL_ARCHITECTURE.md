# POS Portal System - Visual Architecture

## Complete System Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CLIQSERVE BACKEND SYSTEM                          │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  PLATFORM OWNER     │
│  (SaaS Admin)       │
│                     │
│ - Manage all users  │
│ - View all data     │
│ - System config     │
└──────────┬──────────┘
           │
           │ (Admin Dashboard)
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ADMIN INTERFACE / REST API                          │
│                                                                         │
│  POST   /api/users/login/              → Platform Owner Login          │
│  POST   /api/users/                    → Create Users                  │
│  POST   /api/categories/               → Create Categories             │
│  POST   /api/products/                 → Create Products               │
│  POST   /api/pos/devices/              → Register POS Devices          │
│  PUT    /api/users/{id}/               → Assign POS Devices to User    │
│                                                                         │
└─────────────┬──────────────────────────┬──────────────────────────────┘
              │                          │
              ▼                          ▼
     ┌─────────────────┐         ┌──────────────────┐
     │ TENANT ADMIN    │         │ BRANCH MANAGER   │
     │ (Owner)         │         │                  │
     │                 │         │ - Manage branch  │
     │ - Create users  │         │ - View menu      │
     │ - Setup menu    │         │ - Manage cashier │
     │ - Assign dev    │         │                  │
     └────────┬────────┘         └────────┬─────────┘
              │                           │
              └───────────┬───────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │          AUTHENTICATION ENDPOINTS                   │
    │                                                     │
    │  POST /api/users/login/          → Admin Login      │
    │  POST /api/users/pos_login/      → POS Login        │
    │                                                     │
    │  Returns: JWT Token + Accessible Devices            │
    └────────────────┬──────────────────────────────────┘
                     │
      ┌──────────────┴──────────────┐
      │                             │
      ▼                             ▼
  ┌──────────────┐          ┌──────────────────┐
  │  CASHIER 1   │          │  CASHIER 2       │
  │              │          │                  │
  │ Assigned to: │          │ Assigned to:     │
  │ Counter 1    │          │ Counter 2        │
  │              │          │                  │
  │ Can see:     │          │ Can see:         │
  │ - Dev 1 menu │          │ - Dev 2 menu     │
  └──────┬───────┘          └────────┬─────────┘
         │                           │
         └──────────┬────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────┐
    │          POS PORTAL MENU ENDPOINTS              │
    │                                                 │
    │  GET /api/pos/portal/                │
    │      → Categories + Products for user's device │
    │                                                 │
    │  GET /api/pos/portal/categories/          │
    │      → Categories only                         │
    │                                                 │
    │  GET /api/pos/portal/products/            │
    │      → Products (filterable by category)       │
    │                                                 │
    │  GET /api/pos/portal/devices/             │
    │      → User's accessible devices               │
    │                                                 │
    │  GET /api/pos/portal/search/?q=           │
    │      → Search products by name/SKU             │
    │                                                 │
    └────────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────┐
        │   FILTERING PIPELINE             │
        │                                  │
        │ 1. User role check               │
        │    ├─ Cashier/Branch Manager?    │
        │    └─ Not platform/tenant admin  │
        │                                  │
        │ 2. Get user's POS devices        │
        │    ├─ If cashier: assigned devs  │
        │    └─ If manager: branch devs    │
        │                                  │
        │ 3. Filter by tenant              │
        │    └─ Only their restaurant      │
        │                                  │
        │ 4. Filter by branch              │
        │    └─ Only their location        │
        │                                  │
        │ 5. Filter by device restriction  │
        │    ├─ pos_devices IS NULL        │
        │    │  (available everywhere)     │
        │    └─ pos_devices IN user_devs   │
        │       (device-specific)          │
        │                                  │
        │ 6. Filter by status              │
        │    ├─ is_active = TRUE           │
        │    └─ is_available = TRUE        │
        └──────────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │   MENU DATA RETURNED TO POS      │
        │                                  │
        │   {                              │
        │     categories: [                │
        │       {                          │
        │         name: "Appetizers",      │
        │         products: [              │
        │           {                      │
        │             id: 1,               │
        │             name: "Samosas",     │
        │             price: 4.99,         │
        │             ...                  │
        │           }                      │
        │         ]                        │
        │       }                          │
        │     ]                            │
        │   }                              │
        └──────────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │   POS TERMINAL DISPLAYS MENU     │
        │                                  │
        │   Appetizers                     │
        │   ├─ Samosas      $4.99          │
        │   ├─ Spring Rolls $5.99          │
        │                                  │
        │   Main Course                    │
        │   ├─ Butter Chicken $14.99       │
        │   ├─ Tikka Masala   $15.99       │
        │                                  │
        │   (Only shows items available    │
        │    for their device)             │
        └──────────────────────────────────┘
```

---

## Data Model Relationships

```
┌──────────────────────────────────────────────────────────────────┐
│                          DATABASE SCHEMA                         │
└──────────────────────────────────────────────────────────────────┘

TENANTS TABLE
┌──────────────────┐
│ id (PK)          │
│ name             │
│ email            │
│ subscription_plan│
└────────┬─────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────────┐          ┌─────────────────────┐
│  BRANCHES TABLE      │          │   USERS TABLE       │
├──────────────────────┤          ├─────────────────────┤
│ id (PK)              │          │ id (PK)             │
│ tenant_id (FK)       │◄─────────┤ tenant_id (FK)      │
│ name                 │   1:N    │ branch_id (FK)      │
│ code                 │          │ email               │
│ address              │          │ password_hash       │
│ is_active            │          │ role                │
│ created_at           │          │ is_active           │
└────────┬─────────────┘          └──────┬──────────────┘
         │                              │
         │ 1:N                          │ M:N
         │                              │
         ▼                              ▼
┌──────────────────────┐         ┌────────────────────────┐
│  CATEGORIES TABLE    │         │ USERS_POS_DEVICES (J)  │
├──────────────────────┤         ├────────────────────────┤
│ id (PK)              │         │ id (PK)                │
│ tenant_id (FK)       │         │ user_id (FK)           │
│ branch_id (FK)       │         │ posdevice_id (FK)      │
│ name                 │         └────────┬───────────────┘
│ description          │                  │
│ display_order        │                  │
│ is_active            │                  │
└────────┬─────────────┘                  │
         │                                │
         │ M:N                            │
         │                    ┌───────────┘
         ▼                    │
┌──────────────────────┐     │   ┌──────────────────────┐
│ CATEGORIES_POS_DEV(J)│     │   │ POS_DEVICES TABLE    │
├──────────────────────┤     │   ├──────────────────────┤
│ id (PK)              │     │   │ id (PK)              │
│ category_id (FK)     │     │   │ branch_id (FK)       │
│ posdevice_id (FK)    │     │   │ name                 │
└──────────────────────┘     │   │ device_id (unique)   │
                             │   │ device_type          │
         ┌───────────────────┘   │ auth_token           │
         │                       │ status               │
         │                       │ is_active            │
         ▼                       │ last_seen            │
┌──────────────────────┐         └──────────────────────┘
│  PRODUCTS TABLE      │
├──────────────────────┤
│ id (PK)              │
│ tenant_id (FK)       │
│ category_id (FK)     │
│ name                 │
│ sku (unique)         │
│ price                │
│ description          │
│ image                │
│ is_active            │
│ is_available         │
└────────┬─────────────┘
         │
         │ M:N
         │
         ▼
   ┌──────────────────────┐
   │ PRODUCTS_POS_DEV (J)  │
   ├──────────────────────┤
   │ id (PK)              │
   │ product_id (FK)      │
   │ posdevice_id (FK)    │
   └──────────────────────┘
```

---

## Access Control Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER HIERARCHY & PERMISSIONS                 │
└─────────────────────────────────────────────────────────────────┘

LEVEL 1: PLATFORM OWNER
├─ Scope: All Tenants, All Branches, All Users
├─ Access: Admin Dashboard Only
├─ Can: Create tenants, manage all users, view all data
└─ Cannot: Access POS Portal

                        │
                        ▼

LEVEL 2: TENANT ADMIN
├─ Scope: Own Tenant, All Branches, Own Users
├─ Access: Admin Dashboard + REST API
├─ Can: Create/manage users, products, categories, POS devices
├─ Cannot: Access POS Portal, see other tenants
└─ Role enforcement: tenant_id = authenticated_user.tenant_id

                        │
                        ▼

LEVEL 3: BRANCH MANAGER
├─ Scope: Own Tenant, Own Branch, Assigned Users
├─ Access: POS Portal Only
├─ Can: View branch menu, manage cashiers, see inventory
├─ Cannot: Modify products, see other branches
└─ Filtering: tenant = user.tenant AND branch = user.branch

                        │
                        ▼

LEVEL 4: CASHIER
├─ Scope: Own Tenant, Own Branch, Assigned Device Only
├─ Access: POS Terminal/Portal Only
├─ Can: View menu items, process orders
├─ Cannot: Modify anything, see other devices
└─ Filtering: device IN user.pos_devices


FILTERING LOGIC FOR EACH LEVEL:

Platform Owner:
  Categories: ALL
  Products:  ALL
  
Tenant Admin:
  Categories: WHERE tenant_id = user.tenant_id
  Products:  WHERE tenant_id = user.tenant_id
  
Branch Manager:
  Categories: WHERE tenant_id = user.tenant_id
              AND branch_id = user.branch_id
  Products:  WHERE tenant_id = user.tenant_id
              AND (pos_devices IN branch_devices OR pos_devices IS NULL)
  
Cashier:
  Categories: WHERE tenant_id = user.tenant_id
              AND branch_id = user.branch_id
              AND (pos_devices IN user.assigned_devices OR pos_devices IS NULL)
  Products:  WHERE tenant_id = user.tenant_id
              AND (pos_devices IN user.assigned_devices OR pos_devices IS NULL)
              AND is_active = TRUE
              AND is_available = TRUE
```

---

## Real-World Scenario Example

```
PIZZA RESTAURANT: "Pepperoni Palace"
├─ Tenant ID: 1
│
├─ MAIN STREET BRANCH
│  ├─ Branch ID: 1
│  ├─ City: New York
│  │
│  ├─ Counter 1 (Dine-In)
│  │  ├─ Device ID: POS-001
│  │  ├─ Device Type: Tablet
│  │  └─ Operators: [John Cashier]
│  │
│  ├─ Counter 2 (Drive-Thru)
│  │  ├─ Device ID: POS-002
│  │  ├─ Device Type: Desktop
│  │  └─ Operators: [Jane Cashier]
│  │
│  └─ Branch Manager: [Mike Manager]
│     └─ Can see: Menu for Counter 1 + Counter 2
│
├─ MENU STRUCTURE
│  ├─ Category: Pizzas (no device restriction)
│  │  ├─ Product: Margherita      (no device restriction)
│  │  ├─ Product: Pepperoni       (no device restriction)
│  │  └─ Product: Calzone         (Counter 1 only - hard to pack)
│  │
│  ├─ Category: Desserts (no device restriction)
│  │  └─ Product: Tiramisu        (no device restriction)
│  │
│  └─ Category: Alcohol (Counter 1 only - age-restricted)
│     ├─ Product: Beer            (Counter 1 only)
│     └─ Product: Wine            (Counter 1 only)


JOHN'S MENU AT COUNTER 1:
┌──────────────────────────────────┐
│ Pizzas                           │
│ ├─ Margherita        $12.99      │
│ ├─ Pepperoni         $13.99      │
│ └─ Calzone           $14.99      │
│                                  │
│ Desserts                         │
│ └─ Tiramisu          $5.99       │
│                                  │
│ Alcohol                          │
│ ├─ Beer              $4.99       │
│ └─ Wine              $8.99       │
└──────────────────────────────────┘


JANE'S MENU AT COUNTER 2:
┌──────────────────────────────────┐
│ Pizzas                           │
│ ├─ Margherita        $12.99      │
│ └─ Pepperoni         $13.99      │
│                                  │
│ Desserts                         │
│ └─ Tiramisu          $5.99       │
│                                  │
│ (Calzone hidden - Counter 1 only)│
│ (Alcohol section hidden)         │
└──────────────────────────────────┘


WHY THIS MATTERS:
- Drive-thru (Counter 2) doesn't offer Calzone (hard to package)
- Counter 1 can sell alcohol (dine-in with age verification)
- Counter 2 cannot sell alcohol (no age verification at drive-thru)
- Both counters share base pizzas and desserts
- System automatically filters based on device
```

---

## API Request/Response Flow

```
┌─────────────────────┐
│  POS TERMINAL APP   │
└──────────┬──────────┘
           │
           │ POST /api/users/pos_login/
           │ {email: cashier@restaurant.com, password: ***}
           ▼
    ┌───────────────────────┐
    │  AUTHENTICATION       │
    │                       │
    │  Validate credentials │
    │  Check role           │
    │  Check devices        │
    │  Generate JWT         │
    └──────────┬────────────┘
               │
               │ Returns: 200 OK
               │ {
               │   access: "JWT...",
               │   user: {...},
               │   pos_devices: [...]
               │ }
               ▼
        ┌────────────────┐
        │ Store JWT Token│
        │ Store Device ID│
        └────────┬───────┘
                 │
                 │ GET /api/pos/portal/
                 │ Headers: Authorization: Bearer JWT
                 ▼
         ┌────────────────────┐
         │  FILTERING LOGIC   │
         │                    │
         │ 1. Verify JWT      │
         │ 2. Get user info   │
         │ 3. Get devices     │
         │ 4. Filter data     │
         │ 5. Serialize       │
         └─────────┬──────────┘
                   │
                   │ Returns: 200 OK
                   │ {
                   │   categories: [{...}],
                   │   products: [{...}]
                   │ }
                   ▼
        ┌──────────────────────┐
        │  DISPLAY MENU        │
        │  ON POS TERMINAL     │
        │                      │
        │  Show categories     │
        │  Show products       │
        │  Allow selection     │
        │  Process orders      │
        └──────────────────────┘
```

