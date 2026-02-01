# POS Portal - Quick Implementation Guide

## 1. Creating Test Data

### Create Users with Different Roles

```bash
# Platform Owner (You)
POST /api/users/
{
    "email": "admin@saas.com",
    "username": "platformadmin",
    "password": "securepass123",
    "first_name": "Admin",
    "last_name": "User",
    "role": "platform_owner"
}

# Tenant Admin (Restaurant Owner)
POST /api/users/
{
    "email": "owner@restaurant1.com",
    "username": "restaurantowner",
    "password": "securepass123",
    "first_name": "Restaurant",
    "last_name": "Owner",
    "role": "tenant_admin",
    "tenant": 1
}

# Branch Manager
POST /api/users/
{
    "email": "manager@restaurant1.com",
    "username": "branchmanager",
    "password": "securepass123",
    "first_name": "Branch",
    "last_name": "Manager",
    "role": "branch_manager",
    "tenant": 1,
    "branch": 1
}

# Cashier 1 (assigned to Counter 1)
POST /api/users/
{
    "email": "cashier1@restaurant1.com",
    "username": "cashier1",
    "password": "securepass123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "cashier",
    "tenant": 1,
    "branch": 1,
    "pos_devices": [1]  # Counter 1 device ID
}

# Cashier 2 (assigned to Counter 2)
POST /api/users/
{
    "email": "cashier2@restaurant1.com",
    "username": "cashier2",
    "password": "securepass123",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "cashier",
    "tenant": 1,
    "branch": 1,
    "pos_devices": [2]  # Counter 2 device ID
}
```

---

## 2. Login Flows

### Admin Login (Tenant Admin)
```bash
POST /api/users/login/
{
    "email": "owner@restaurant1.com",
    "password": "securepass123"
}

# Response: JWT token + full user profile
# Can now: Create products, manage categories, assign devices to users
```

### POS Terminal Login (Cashier)
```bash
POST /api/users/pos_login/
{
    "email": "cashier1@restaurant1.com",
    "password": "securepass123",
    "device_id": "POS-001"
}

# Response includes:
# - JWT token
# - List of accessible POS devices
# - Ready for menu retrieval
```

---

## 3. Creating Menu Structure

### Step 1: Create Categories (as Tenant Admin)
```bash
# Authenticate as tenant_admin first
POST /api/categories/
{
    "name": "Appetizers",
    "description": "Starters and appetizers",
    "display_order": 1,
    "is_active": true,
    "branch": 1,
    "pos_devices": []  # Empty = available on ALL devices
}

POST /api/categories/
{
    "name": "Main Course",
    "description": "Main dishes",
    "display_order": 2,
    "is_active": true,
    "branch": 1,
    "pos_devices": []
}

# Device-specific category
POST /api/categories/
{
    "name": "Alcohol",
    "description": "Alcoholic beverages (Counter 1 only)",
    "display_order": 5,
    "is_active": true,
    "branch": 1,
    "pos_devices": [1]  # Only Counter 1 can sell alcohol
}
```

### Step 2: Create Products
```bash
POST /api/products/
{
    "name": "Samosas",
    "sku": "APP-001",
    "description": "Crispy vegetable samosas",
    "price": "4.99",
    "category": 1,  # Appetizers
    "is_active": true,
    "is_available": true,
    "pos_devices": []  # Available on all devices
}

POST /api/products/
{
    "name": "Butter Chicken",
    "sku": "MC-001",
    "description": "Tender chicken in creamy butter sauce",
    "price": "14.99",
    "category": 2,  # Main Course
    "is_active": true,
    "is_available": true,
    "pos_devices": []
}

# Device-specific product
POST /api/products/
{
    "name": "House Wine",
    "sku": "ALC-001",
    "description": "Red wine - Counter 1 only",
    "price": "7.99",
    "category": 3,  # Alcohol
    "is_active": true,
    "is_available": true,
    "pos_devices": [1]  # Only Counter 1 sells this
}
```

---

## 4. Accessing POS Portal Menu

### Cashier 1 (Counter 1) - with Authorization Header
```bash
# After pos_login, use the returned JWT token
GET /api/pos/portal/
Authorization: Bearer <JWT_TOKEN>

# Response: Menu for Counter 1
# - Appetizers (available to all devices) ✓ Shows
# - Main Course (available to all devices) ✓ Shows
# - Alcohol (Counter 1 only) ✓ Shows
# - House Wine product ✓ Shows

# Products seen:
# - Samosas ✓
# - Butter Chicken ✓
# - House Wine ✓ (only because it's Counter 1)
```

### Cashier 2 (Counter 2) - Different Menu
```bash
GET /api/pos/portal/
Authorization: Bearer <CASHIER2_JWT>

# Response: Menu for Counter 2
# - Appetizers ✓ Shows
# - Main Course ✓ Shows
# - Alcohol ✗ NOT shown (Counter 1 only)

# Products seen:
# - Samosas ✓
# - Butter Chicken ✓
# - House Wine ✗ (not visible at Counter 2)
```

---

## 5. Advanced Filtering Examples

### Get Products by Category
```bash
GET /api/pos/portal/products/?category_id=1
Authorization: Bearer <JWT>

# Returns only products in Appetizers category
# that the user has access to
```

### Search Products
```bash
GET /api/pos/portal/search/?q=butter
Authorization: Bearer <JWT>

# Returns:
# - Butter Chicken (if accessible to user)
# - Any other product containing "butter"
```

### List User's Devices
```bash
GET /api/pos/portal/devices/
Authorization: Bearer <JWT>

# Response for Cashier 1:
{
    "count": 1,
    "devices": [
        {
            "id": 1,
            "name": "Counter 1",
            "device_id": "POS-001",
            "device_type": "tablet",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        }
    ]
}

# Response for Branch Manager:
{
    "count": 2,
    "devices": [
        {
            "id": 1,
            "name": "Counter 1",
            "device_id": "POS-001",
            ...
        },
        {
            "id": 2,
            "name": "Counter 2",
            "device_id": "POS-002",
            ...
        }
    ]
}
```

---

## 6. Access Control Examples

### ✅ What Cashier 1 CAN Do
- View menu for Counter 1 ✓
- See products assigned to Counter 1 or all devices ✓
- Use POS portal ✓
- Cannot manage users, products, or categories ✗

### ✅ What Cashier 2 CAN Do
- View menu for Counter 2 ✓
- See products assigned to Counter 2 or all devices ✓
- Cannot see Counter 1 exclusive products ✗
- Cannot create/modify anything ✗

### ✅ What Branch Manager CAN Do
- View menu for all devices in their branch ✓
- Create/manage cashier users ✓
- View inventory for branch ✓
- Cannot create/modify products or categories ✗
- Cannot see other branches ✗

### ✅ What Tenant Admin CAN Do
- Create products and categories ✓
- Assign products to specific devices ✓
- Manage users (admins, managers, cashiers) ✓
- Cannot access POS terminal ✗
- Cannot see other tenants ✗

### ✅ What Platform Owner CAN Do
- Everything across all tenants ✓
- Manage other administrators ✓
- View system statistics ✓

---

## 7. Common POS Terminal Workflow

```javascript
// 1. Login
POST /api/users/pos_login/
Body: {email, password, device_id}
Store: JWT token, list of devices

// 2. Get Menu
GET /api/pos/portal/
Headers: {Authorization: Bearer JWT}
Display: Categories and products organized by category

// 3. Search Product
GET /api/pos/portal/search/?q="butter"
Headers: {Authorization: Bearer JWT}
Display: Matching products

// 4. Get Category Products (optional)
GET /api/pos/portal/products/?category_id=2
Headers: {Authorization: Bearer JWT}
Display: Products in Main Course category

// 5. Create Order (future endpoint)
POST /api/orders/
Body: {items: [{product_id, qty, price}]}
Headers: {Authorization: Bearer JWT}
Create: Order record

// 6. Logout
POST /api/token/blacklist/ (or just discard JWT)
```

---

## 8. Troubleshooting

### Cashier Sees Nothing
**Possible causes:**
1. Not assigned to any POS device
   - Fix: Add device ID to user.pos_devices

2. No categories/products created for their branch
   - Fix: Create categories with branch assignment

3. Categories/products have wrong device assignment
   - Fix: Update pos_devices field

4. User is disabled (is_active=False)
   - Fix: Set is_active=True

### "No POS devices assigned" error
- User is cashier with empty pos_devices field
- User is branch_manager with no pos_devices and no branch assigned
- Solution: Assign appropriate POS devices or branch

### Wrong menu appears
- Category/Product restricted to different device
- User's branch doesn't match category branch
- Solution: Check pos_devices and branch assignments

---

## 9. Database Queries Reference

### Check User's Accessible Devices
```sql
SELECT * FROM pos_devices 
WHERE operators.user_id = 123 AND is_active = TRUE;
```

### Check User's Accessible Categories
```sql
SELECT DISTINCT c.* FROM categories c
LEFT JOIN pos_devices pd ON c.pos_devices.id = pd.id
WHERE c.tenant_id = 1 
  AND c.branch_id = 1 
  AND c.is_active = TRUE
  AND (c.pos_devices IS NULL 
       OR pd.operators.user_id = 123);
```

### Check User's Accessible Products
```sql
SELECT DISTINCT p.* FROM products p
LEFT JOIN pos_devices pd ON p.pos_devices.id = pd.id
WHERE p.tenant_id = 1 
  AND p.is_active = TRUE 
  AND p.is_available = TRUE
  AND (p.pos_devices IS NULL 
       OR pd.operators.user_id = 123);
```

