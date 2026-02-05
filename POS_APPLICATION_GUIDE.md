# POS Application Overview

## 📱 What is Your POS Application?

Your POS (Point of Sale) application is a **multi-tenant, role-based terminal system** that allows restaurants/businesses to manage:
- **POS Devices** - Physical terminals (tablets, desktops, mobile)
- **Device Access Control** - Who can use which devices
- **Menu Management** - What products are available on each device
- **Device Status Tracking** - Online/offline monitoring

---

## 🏗️ POS Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    POS APPLICATION LAYER                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         POS Portal (Cashier/Manager View)           │  │
│  │  └─ Read-only menu viewing                          │  │
│  │  └─ Device-specific filtering                       │  │
│  │  └─ Category/Product filtering                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      POS Device Management (Admin View)             │  │
│  │  └─ Create/Update POS devices                       │  │
│  │  └─ Activate/Deactivate devices                     │  │
│  │  └─ Token generation                               │  │
│  │  └─ Status monitoring (ping/heartbeat)              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 POS App File Structure

```
apps/pos/
├── models.py                    # POSDevice model
├── serializers.py               # POSDeviceSerializer, DeviceLoginSerializer
├── permissions.py               # POSPortalPermission, access control
├── urls.py                      # URL routing
├── admin.py                     # Django admin config
├── portal_status_views.py        # POSPortalMenuViewSet (Main view)
└── views/
    ├── __init__.py              # Exports all view classes
    ├── views.py                 # POSDeviceViewSet, DeviceViewSet
    ├── base.py                  # BasePosDeviceAPIView (Base class)
    └── status.py                # PosDeviceStatusMixin (Status tracking)
```

---

## 🎯 Key Components

### 1. **POSDevice Model** (`models.py`)
```python
class POSDevice(models.Model):
    # Relationships
    branch          # Branch this device belongs to
    tenant          # Tenant (multi-tenant support)
    assigned_to     # Optional: specific user assigned
    
    # Device Info
    name            # e.g., "Counter 1", "Drive-thru"
    device_id       # Unique identifier
    device_type     # tablet, desktop, mobile
    
    # Status Tracking
    status          # online, offline, maintenance, suspended
    is_active       # Enable/disable device
    last_seen       # Last heartbeat timestamp
    ip_address      # Device IP address
    
    # Authentication
    auth_token      # Device authentication token
    public_url      # Generated URL for this device
```

---

### 2. **POS Device Endpoints** (Management)

**Base:** `/api/pos/devices/manage/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/pos/devices/manage/` | GET | List all POS devices (filtered by role) |
| `/api/pos/devices/manage/` | POST | Create new POS device |
| `/api/pos/devices/manage/{id}/` | GET | Get device details |
| `/api/pos/devices/manage/{id}/` | PUT/PATCH | Update device |
| `/api/pos/devices/manage/{id}/` | DELETE | Delete device |
| `/api/pos/devices/manage/{id}/activate/` | POST | Activate device |
| `/api/pos/devices/manage/{id}/deactivate/` | POST | Deactivate device |
| `/api/pos/devices/manage/{id}/ping/` | POST | Update device status/heartbeat |
| `/api/pos/devices/manage/{id}/generate_token/` | POST | Generate auth token |
| `/api/pos/devices/manage/online/` | GET | Get all online devices |

**Required Permission:** `IsAuthenticated` (admin/manager only)

---

### 3. **POS Portal Endpoints** (Cashier/Manager View)

**Base:** `/api/pos/portal/`

| Endpoint | Method | Purpose | Who Can Access |
|----------|--------|---------|-----------------|
| `/api/pos/portal/` | GET | Complete menu (categories + products) | Cashiers, Branch Managers |
| `/api/pos/portal/categories/` | GET | Get categories for assigned devices | Cashiers, Branch Managers |
| `/api/pos/portal/products/` | GET | Get products for assigned devices | Cashiers, Branch Managers |
| `/api/pos/portal/devices/` | GET | Get user's accessible POS devices | Cashiers, Branch Managers |
| `/api/pos/portal/search/?q=...` | GET | Search products by name | Cashiers, Branch Managers |

**Required Permission:** `POSPortalPermission` (cashier/branch_manager only)

**Features:**
- ✅ Device-level filtering (only products for assigned devices)
- ✅ Tenant isolation (only user's tenant data)
- ✅ Branch isolation (only user's branch data)
- ✅ Product/Category restrictions
- ✅ Search functionality

---

### 4. **POS Serializers** (`serializers.py`)

```python
# POSDeviceSerializer
- Serializes POSDevice model
- Includes calculated fields: is_online, branch_name
- Generates: public_url, login_url

# DeviceLoginSerializer
- Accepts username/password OR device_id/auth_token
- Used for device authentication

# POSPortalDeviceSerializer
- Lightweight device info for POS portal
- Filters sensitive data
```

---

### 5. **Access Control** (`permissions.py`)

**POSPortalPermission Class:**
```python
✅ Platform Owner       → Redirected to admin interface
✅ Tenant Admin        → Redirected to admin interface
✅ Branch Manager      → Access POS Portal (own branch devices)
✅ Cashier             → Access POS Portal (assigned devices only)
```

**Filtering Logic:**
1. User role check (cashier/branch_manager)
2. Tenant isolation
3. Branch isolation
4. Device assignment verification

---

## 🔄 Data Flow Examples

### Example 1: Cashier Accesses Menu

```
Cashier Login
    ↓
POST /api/users/login/
    ↓
JWT Token Generated (with role=cashier, tenant=1, branch=2)
    ↓
GET /api/pos/portal/
    ↓
Permission Check (POSPortalPermission)
    └─ Is authenticated? ✓
    └─ Is cashier/branch_manager? ✓
    └─ Has assigned devices? ✓
    ↓
Get User's Devices (from user.pos_devices)
    └─ Device #1 (Counter 1)
    └─ Device #2 (Drive-thru)
    ↓
Filter Categories
    WHERE tenant=1 
    AND branch=2
    AND is_active=True
    AND (pos_devices IN [Device#1, Device#2] OR pos_devices IS NULL)
    ↓
Filter Products
    WHERE tenant=1
    AND branch=2
    AND is_active=True
    AND (pos_devices IN [Device#1, Device#2] OR pos_devices IS NULL)
    ↓
Response: Categories with Products
{
  "count": 5,
  "categories": [
    {
      "id": 1,
      "name": "Beverages",
      "products": [
        {"id": 10, "name": "Coffee", "price": 2.50},
        {"id": 11, "name": "Tea", "price": 2.00}
      ]
    }
  ]
}
```

### Example 2: Admin Activates Device

```
Admin Login
    ↓
GET /api/pos/devices/manage/5/
    ↓
Permission Check (IsAuthenticated, CanManageDevice)
    ↓
Retrieve Device #5
    ↓
POST /api/pos/devices/manage/5/activate/
    ↓
Set: is_active=True, status='online'
    ↓
Save & Return Device
{
  "id": 5,
  "name": "Counter 1",
  "device_id": "POS-001",
  "is_active": true,
  "status": "online",
  "last_seen": "2026-02-03T10:30:45Z"
}
```

---

## 📊 Permission Matrix

```
┌─────────────────┬──────────────┬────────────────┬─────────────┐
│   User Role     │ Device Mgmt  │ POS Portal     │ Can Access  │
├─────────────────┼──────────────┼────────────────┼─────────────┤
│ Platform Owner  │ ✓ All        │ ✗ Redirected  │ Admin only  │
│ Tenant Admin    │ ✓ Their      │ ✗ Redirected  │ Admin only  │
│                 │   tenant     │                │             │
│ Branch Manager  │ ✗ Limited    │ ✓ Their       │ POS Portal  │
│                 │   read       │   devices     │             │
│ Cashier         │ ✗ No         │ ✓ Assigned    │ POS Portal  │
│                 │   access     │   devices     │             │
└─────────────────┴──────────────┴────────────────┴─────────────┘
```

---

## 🔗 Device Assignment Flow

```
1. Create POS Device
   └─ Associated with: Branch → Tenant

2. Assign Device to User
   └─ user.pos_devices.add(device)
   └─ Only cashiers/branch_managers

3. Cashier Logs In
   └─ POST /api/users/pos_login/
   └─ Validates assigned devices
   └─ Returns accessible device list

4. Cashier Accesses Portal
   └─ GET /api/pos/portal/
   └─ Filters based on assigned devices
   └─ Only shows relevant menu items

5. Device Heartbeat
   └─ POST /api/pos/devices/manage/{id}/ping/
   └─ Updates: last_seen, status
   └─ Tracks device online/offline status
```

---

## 🔐 Security Features

1. **Device Authentication**
   - Auth token per device
   - Token can be regenerated
   - Device ID + Auth Token required

2. **Role-Based Access**
   - POSPortalPermission class enforces roles
   - Cashiers limited to assigned devices
   - Managers limited to their branch

3. **Multi-Tenant Isolation**
   - All queries filtered by tenant
   - Branch isolation within tenant
   - Device assignment verification

4. **Status Tracking**
   - Online/offline monitoring
   - IP address logging
   - Last seen timestamp

---

## 📈 Key Views & ViewSets

### POSDeviceViewSet
- Full CRUD for POS devices
- Management endpoints (activate, deactivate, ping, generate_token)
- Online device listing
- Permission: IsAuthenticated

### DeviceViewSet (Read-only)
- List/retrieve devices
- Public read endpoints
- Permission: IsAuthenticated

### POSPortalMenuViewSet (Main POS Interface)
- Categories endpoint
- Products endpoint
- Device list endpoint
- Search endpoint
- Permission: POSPortalPermission

---

## 🛠️ How Filtering Works

**Category Filtering:**
```python
categories = Category.objects.filter(
    tenant=user.tenant,              # ✓ Same tenant
    branch=user.branch,              # ✓ Same branch
    is_active=True                   # ✓ Active
).filter(
    Q(pos_devices__in=devices) |     # Available on user's devices
    Q(pos_devices__isnull=True)      # OR available on all devices
).distinct()
```

**Product Filtering:**
```python
products = Product.objects.filter(
    tenant=user.tenant,              # ✓ Same tenant
    is_active=True,                  # ✓ Active
    category__branch=user.branch     # ✓ Same branch
).filter(
    Q(pos_devices__in=devices) |     # Available on user's devices
    Q(pos_devices__isnull=True)      # OR available on all devices
).distinct()
```

---

## 📝 API Response Examples

### GET /api/pos/portal/
```json
{
  "count": 3,
  "categories": [
    {
      "id": 1,
      "name": "Hot Beverages",
      "description": "Coffee, tea, etc.",
      "display_order": 1,
      "is_active": true,
      "products": [
        {
          "id": 10,
          "name": "Espresso",
          "sku": "ESP-001",
          "price": "3.50",
          "description": "Strong coffee",
          "image": "/media/products/espresso.jpg",
          "is_available": true
        }
      ]
    }
  ]
}
```

### GET /api/pos/portal/devices/
```json
{
  "count": 2,
  "devices": [
    {
      "id": 1,
      "name": "Counter 1",
      "device_id": "POS-001",
      "device_type": "tablet",
      "status": "online",
      "is_active": true,
      "is_online": true,
      "ip_address": "192.168.1.10"
    }
  ]
}
```

### POST /api/pos/devices/manage/1/activate/
```json
{
  "id": 1,
  "name": "Counter 1",
  "device_id": "POS-001",
  "status": "online",
  "is_active": true,
  "is_online": true,
  "last_seen": "2026-02-03T10:30:45Z"
}
```

---

## 🚀 Current Status

✅ **Implemented:**
- POSDevice model with all relationships
- Device management endpoints (CRUD)
- Device activation/deactivation
- Token generation
- POS portal with filtering
- Product/Category search
- Device status tracking
- Multi-tenant support
- Role-based access control

⚠️ **Needs Work:**
- See ARCHITECTURE_REVIEW.md for details
- Tests for POS endpoints
- Rate limiting on device endpoints
- Better error handling in views

---

## 💡 Usage Scenarios

### Scenario 1: Restaurant Opening
1. Admin creates POS devices (Counter 1, Counter 2, Drive-thru)
2. Cashier arrives and logs in with their credentials
3. System assigns them to their designated device
4. Cashier accesses portal to see available menu items
5. Cashier can process orders

### Scenario 2: Menu Configuration
1. Admin assigns specific products only to "Drive-thru" device
2. Cashier at Counter 1 won't see Drive-thru-only items
3. Drive-thru operator will see all their assigned items
4. Real-time filtering based on device assignment

### Scenario 3: Device Monitoring
1. Admin checks online devices: `GET /api/pos/devices/manage/online/`
2. Device sends heartbeat every 30 seconds: `POST /api/pos/devices/manage/{id}/ping/`
3. If no heartbeat for 5 minutes → device marked offline
4. Admin gets alert if critical device goes offline

