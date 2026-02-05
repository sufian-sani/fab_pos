# POS Views Structure & Architecture

## 📁 Directory Layout

```
apps/pos/views/
├── __init__.py              # Exports all view classes
├── views.py                 # Main ViewSets (POSDeviceViewSet, DeviceViewSet, etc.)
├── base.py                  # Base classes (BasePosDeviceAPIView)
└── status.py                # Mixins (PosDeviceStatusMixin)
```

---

## 🔍 Detailed View Breakdown

### 1. **__init__.py** - View Exports

```python
from .views import (
    POSDeviceViewSet,              # Main device management
    DeviceViewSet,                 # Read-only device view
    DeviceLogoutAPIView,           # Device logout
    MyDevicesAPIView,              # Get user's devices
    DeviceHeartbeatAPIView,        # Heartbeat tracking
    DeviceStatusAPIView,           # Check device status
)

from .base import BasePosDeviceAPIView
from .status import PosDeviceStatusMixin

# Combined API View
class PosDeviceAPIView(
    PosDeviceStatusMixin,          # Mixin for status endpoints
    BasePosDeviceAPIView,          # Base class with retrieve logic
):
    pass
```

**Purpose:** Centralizes all POS view exports for clean imports.

---

### 2. **views.py** - Core ViewSets

#### **POSDeviceViewSet** (CRUD + Actions)
**Purpose:** Full management of POS devices

**Endpoints:**
```
GET    /api/pos/devices/manage/              # List devices
POST   /api/pos/devices/manage/              # Create device
GET    /api/pos/devices/manage/{id}/         # Get device
PUT    /api/pos/devices/manage/{id}/         # Update device
PATCH  /api/pos/devices/manage/{id}/         # Partial update
DELETE /api/pos/devices/manage/{id}/         # Delete device

POST   /api/pos/devices/manage/{id}/activate/       # Activate
POST   /api/pos/devices/manage/{id}/deactivate/     # Deactivate
POST   /api/pos/devices/manage/{id}/ping/           # Heartbeat
POST   /api/pos/devices/manage/{id}/generate_token/ # Gen token
GET    /api/pos/devices/manage/online/              # Online devices
```

**Key Methods:**
```python
class POSDeviceViewSet(viewsets.ModelViewSet):
    
    def get_queryset(self):
        # Filter by user role:
        # Platform Owner → All devices
        # Tenant Admin → Devices in their tenant
        # Branch Manager → Devices in their branch
        
    def perform_create(self, serializer):
        # Validate branch access
        # Generate auth token if needed
        
    @action(detail=True, methods=['post'])
    def activate(self):
        # Set is_active=True, status='online'
        
    @action(detail=True, methods=['post'])
    def deactivate(self):
        # Set is_active=False, status='offline'
        
    @action(detail=True, methods=['post'])
    def ping(self):
        # Update last_seen, status='online'
        # Get IP address
        
    @action(detail=True, methods=['post'])
    def generate_token(self):
        # Generate new auth_token
        
    @action(detail=False, methods=['get'])
    def online(self):
        # Get all online devices
```

**Permissions:** `IsAuthenticated`

**Filtering:** By role (platform_owner, tenant_admin, branch_manager)

---

#### **DeviceViewSet** (Read-Only)
**Purpose:** Public read-only device endpoints

**Endpoints:**
```
GET  /api/pos/devices/              # List devices (filtered)
GET  /api/pos/devices/{id}/         # Get device details
```

**Key Features:**
- Read-only (no POST/PUT/DELETE)
- Uses `viewsets.ReadOnlyModelViewSet`
- Filters by user role
- Registered under `devices` namespace

**Permissions:** `POSPortalPermission`

---

#### **MyDevicesAPIView** (Custom APIView)
**Purpose:** Get devices accessible by current authenticated user

**Endpoint:**
```
GET /api/pos/my_devices/
```

**Response:**
```json
{
  "count": 3,
  "devices": [
    {
      "id": 1,
      "name": "Counter 1",
      "device_id": "POS-001",
      "status": "online",
      "is_online": true,
      "is_active": true
    }
  ]
}
```

**Logic:**
- Platform Owner → All devices
- Tenant Admin → Devices in tenant
- Branch Manager → Devices in branch + assigned devices
- Assigned Devices → User's explicitly assigned devices

**Permissions:** `IsAuthenticated`

---

### 3. **base.py** - Base Classes

#### **BasePosDeviceAPIView** (ViewSet Base)
**Purpose:** Base class for tenant-scoped device operations

**Key Methods:**
```python
class BasePosDeviceAPIView(viewsets.ViewSet):
    
    lookup_field = 'device_id'
    permission_classes = [POSPortalPermission]
    
    def get_object(self):
        # Get device by tenant_id + device_id
        # Validate tenant match
        # Return active device with relations
        
    def retrieve(self, request, tenant_id=None, device_id=None):
        # GET /api/pos/tenants/{tenant_id}/devices/{device_id}/
        # Returns detailed device info + branch + tenant + assigned_to
```

**Response Format:**
```json
{
  "success": true,
  "device": {
    "id": 1,
    "device_id": "POS-001",
    "name": "Counter 1",
    "status": "online",
    "is_online": true,
    "public_url": "https://pos.example.com/devices/POS-001/"
  },
  "branch": {
    "id": 1,
    "name": "Downtown Branch",
    "code": "DT-001",
    "address": "123 Main St",
    "phone": "+1234567890"
  },
  "tenant": {
    "id": 1,
    "name": "My Restaurant",
    "domain": "myrestaurant.com"
  },
  "assigned_to": {
    "id": 5,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

---

### 4. **status.py** - Mixin Classes

#### **PosDeviceStatusMixin** (Action Mixin)
**Purpose:** Add status-checking action to views

**Methods:**
```python
class PosDeviceStatusMixin:
    
    @action(detail=True, methods=['get'], url_path='check_status')
    def check_status(self, request, *args, **kwargs):
        # GET /api/pos/devices/{id}/check_status/
        # Returns: status, is_online, last_seen
```

**Response:**
```json
{
  "success": true,
  "device_id": "POS-001",
  "status": "online",
  "is_online": true,
  "last_seen": "2026-02-03T10:30:45Z"
}
```

---

## 🔗 Device-Specific Endpoints

These endpoints use the `device_id` path parameter:

### **DeviceLogoutAPIView**
**Purpose:** Logout a device session

**Endpoint:**
```
POST /api/pos/tenants/{tenant_id}/devices/{device_id}/logout/
```

**Headers:**
```
X-POS-Token: device-auth-token
```

**Response:**
```json
{
  "success": true,
  "message": "Device logged out successfully",
  "device_id": "POS-001"
}
```

**Logic:**
1. Extract X-POS-Token from headers
2. Find device matching device_id + tenant_id + auth_token
3. Set status='offline'
4. Return success

---

### **DeviceHeartbeatAPIView**
**Purpose:** Update device heartbeat (keep-alive signal)

**Endpoint:**
```
POST /api/pos/tenants/{tenant_id}/devices/{device_id}/heartbeat/
```

**Headers:**
```
X-POS-Token: device-auth-token
```

**Response:**
```json
{
  "success": true,
  "last_seen": "2026-02-03T10:30:45Z",
  "is_online": true,
  "status": "online"
}
```

**Logic:**
1. Extract X-POS-Token from headers
2. Find device matching device_id + tenant_id + auth_token
3. Update last_seen = now()
4. Set status='online'
5. Return updated status

**Usage:** Device sends heartbeat every 30 seconds to mark itself as online

---

### **DeviceStatusAPIView**
**Purpose:** Check device status (public endpoint)

**Endpoint:**
```
GET /api/pos/tenants/{tenant_id}/devices/{device_id}/status/
```

**Headers (Optional):**
```
X-POS-Token: device-auth-token
```

**Response (Without Token):**
```json
{
  "success": true,
  "device_id": "POS-001",
  "name": "Counter 1",
  "status": "online",
  "is_online": true,
  "is_active": true
}
```

**Response (With Valid Token):**
```json
{
  "success": true,
  "device_id": "POS-001",
  "name": "Counter 1",
  "status": "online",
  "is_online": true,
  "is_active": true,
  "branch": {
    "id": 1,
    "name": "Downtown"
  },
  "tenant": {
    "id": 1,
    "name": "My Restaurant"
  },
  "last_seen": "2026-02-03T10:30:45Z",
  "device_type": "tablet",
  "ip_address": "192.168.1.10"
}
```

**Logic:**
1. Find device by device_id + tenant_id
2. If no token → return basic info
3. If valid token → return detailed info

---

## 🎯 View Hierarchy & Inheritance

```
APIView
├── MyDevicesAPIView
├── DeviceLogoutAPIView
├── DeviceHeartbeatAPIView
└── DeviceStatusAPIView

ViewSet
├── BasePosDeviceAPIView (with retrieve())
│   ├── PosDeviceAPIView (with StatusMixin)
│
├── POSDeviceViewSet (ModelViewSet)
│   └── Full CRUD + custom actions
│
└── DeviceViewSet (ReadOnlyModelViewSet)
    └── Read-only list/retrieve
```

---

## 📊 ViewSet vs APIView

| Feature | ViewSet | APIView |
|---------|---------|---------|
| **Usage** | CRUD operations | Custom logic |
| **Inheritance** | ModelViewSet, ViewSet | APIView |
| **Routing** | Router auto-routes | Manual url paths |
| **Methods** | list, create, retrieve, update, destroy | get, post, put, patch, delete |
| **Examples** | POSDeviceViewSet, DeviceViewSet | DeviceLogoutAPIView, DeviceStatusAPIView |

---

## 🔐 Permissions Applied

### **POSDeviceViewSet**
- `permission_classes = [IsAuthenticated]`
- Filters by: platform_owner, tenant_admin, branch_manager, cashier

### **DeviceViewSet**
- `permission_classes = [POSPortalPermission]`
- Restricts to: cashiers, branch_managers

### **Device-Specific Endpoints**
- `permission_classes = [AllowAny]` (with token validation)
- Validates: X-POS-Token header
- Used by: POS device apps directly

### **MyDevicesAPIView**
- `permission_classes = [IsAuthenticated]`
- Returns user-accessible devices

---

## 🚀 API Request Flow

### **Flow 1: Admin Creates Device**
```
1. POST /api/pos/devices/manage/
   ├─ Permission: IsAuthenticated ✓
   ├─ Data: {name, device_id, branch, device_type}
   ├─ Validate: User can access this branch
   ├─ Create: POSDevice object
   ├─ Generate: auth_token
   └─ Return: Device data with token

2. Response:
   {
     "id": 1,
     "name": "Counter 1",
     "device_id": "POS-001",
     "auth_token": "eyJ0eXAi...",
     "status": "offline",
     "is_active": true
   }
```

### **Flow 2: POS Device Sends Heartbeat**
```
1. POST /api/pos/tenants/1/devices/POS-001/heartbeat/
   ├─ Headers: X-POS-Token: eyJ0eXAi...
   ├─ Find: Device by tenant_id + device_id + auth_token
   ├─ Validate: Token matches
   ├─ Update: last_seen = now(), status = 'online'
   └─ Save: Device

2. Response:
   {
     "success": true,
     "last_seen": "2026-02-03T10:30:45Z",
     "status": "online",
     "is_online": true
   }
```

### **Flow 3: Cashier Gets Portal Menu**
```
1. GET /api/pos/portal/
   ├─ Permission: POSPortalPermission ✓
   ├─ Get: User's assigned devices
   ├─ Filter: Categories for devices
   ├─ Filter: Products for devices
   └─ Return: Organized menu

2. Response:
   {
     "count": 3,
     "categories": [
       {
         "id": 1,
         "name": "Beverages",
         "products": [...]
       }
     ]
   }
```

---

## 📝 Common Patterns in Views

### **Pattern 1: Permission Checking**
```python
def get_queryset(self):
    user = self.request.user
    
    if user.is_platform_owner:
        return POSDevice.objects.all()
    
    if user.is_tenant_admin:
        return POSDevice.objects.filter(tenant=user.tenant)
    
    if user.is_branch_manager:
        return POSDevice.objects.filter(branch=user.branch)
    
    return POSDevice.objects.none()
```

### **Pattern 2: Custom Actions**
```python
@action(detail=True, methods=['post'])
def custom_action(self, request, pk=None):
    obj = self.get_object()
    # Do something with obj
    return Response({'status': 'success'})
```

### **Pattern 3: Token Validation**
```python
device_token = request.META.get('HTTP_X_POS_TOKEN')
if not device_token:
    return Response({'error': 'Token required'}, status=400)

device = POSDevice.objects.get(auth_token=device_token)
```

### **Pattern 4: Response with Success Flag**
```python
return Response({
    'success': True,
    'data': {...},
    'message': 'Operation successful'
}, status=status.HTTP_200_OK)
```

---

## 🔄 Complete View Lookup

| View | Type | Purpose | Key Endpoint |
|------|------|---------|-------------|
| POSDeviceViewSet | ModelViewSet | Full device management | `/api/pos/devices/manage/` |
| DeviceViewSet | ReadOnlyViewSet | Read-only device access | `/api/pos/devices/` |
| MyDevicesAPIView | APIView | Get user's devices | `/api/pos/my_devices/` |
| DeviceLogoutAPIView | APIView | Logout device | `/api/pos/tenants/{id}/devices/{id}/logout/` |
| DeviceHeartbeatAPIView | APIView | Device keep-alive | `/api/pos/tenants/{id}/devices/{id}/heartbeat/` |
| DeviceStatusAPIView | APIView | Check status | `/api/pos/tenants/{id}/devices/{id}/status/` |
| BasePosDeviceAPIView | ViewSet | Base for tenant scoping | Used as base class |
| PosDeviceStatusMixin | Mixin | Add status action | Mixed into PosDeviceAPIView |

---

## 🎯 Summary

Your POS views are **well-organized and follow Django best practices**:

✅ **Separation of Concerns**
- ViewSets for CRUD operations
- APIViews for custom logic
- Mixins for reusable behavior

✅ **Flexible Permissions**
- Role-based filtering
- Token-based device auth
- Proper permission classes

✅ **Clean Architecture**
- Views in dedicated files
- Proper inheritance hierarchy
- Clear action decorators

⚠️ **Areas for Improvement**
- Add comprehensive error handling
- Add request validation/serializers
- Add unit tests
- Add logging
- Add rate limiting on device endpoints

