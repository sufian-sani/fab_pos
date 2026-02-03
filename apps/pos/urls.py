# ============================================================================
# apps/pos/urls.py - UPDATED to work with your existing code
# ============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    POSDeviceViewSet,
    DeviceViewSet,
    DeviceLogoutAPIView,
    DeviceHeartbeatAPIView,
    DeviceStatusAPIView,
    MyDevicesAPIView,
    PosDeviceAPIView,
)
from .portal_status_views import POSPortalMenuViewSet

#main view
# from .views import (
#     POSDeviceViewSet,
#     PosDeviceAPIView
#     )

router = DefaultRouter()

# Public read-only device endpoints
router.register(r'devices', DeviceViewSet, basename='device')

# Full management endpoints kept under a separate prefix
router.register(r'devices/manage', POSDeviceViewSet, basename='pos-device')

# Portal endpoints (for POS interface)
router.register(r'portal', POSPortalMenuViewSet, basename='pos-portal')


# router.register(r'tenants/(?P<tenant_id>\d+)/devices', DeviceLoginAPIView, basename='tenant-devices')
# router.register(r'tenants/(?P<tenant_id>\d+)/devices', PosDeviceAPIView, basename='tenant-devices')
router.register(r'tenants/(?P<tenant_id>\d+)/device', PosDeviceAPIView, basename='tenant-device')

# path(
#         'tenants/<int:tenant_id>/devices/<str:device_id>/login/',
#         DeviceLoginAPIView.as_view(),
#         name='device-login'
#     ),
    # path(
    #     'tenants/<int:tenant_id>/devices/<str:device_id>/check_status/',
    #     DeviceLoginAPIView.as_view(),
    #     name='device-check-status'
    # ),

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Device authentication endpoints
    # path(
    #     'tenants/<int:tenant_id>/devices/<str:device_id>/login/',
    #     DeviceLoginAPIView.as_view(),
    #     name='device-login'
    # ),
    # path(
    #     'tenants/<int:tenant_id>/devices/<str:device_id>/check_status/',
    #     DeviceLoginAPIView.as_view(),
    #     name='device-check-status'
    # ),
    path(
        'tenants/<int:tenant_id>/devices/<str:device_id>/logout/',
        DeviceLogoutAPIView.as_view(),
        name='device-logout'
    ),
    path(
        'tenants/<int:tenant_id>/devices/<str:device_id>/status/',
        DeviceStatusAPIView.as_view(),
        name='device-status'
    ),
    path(
        'tenants/<int:tenant_id>/devices/<str:device_id>/heartbeat/',
        DeviceHeartbeatAPIView.as_view(),
        name='device-heartbeat'
    ),
    
    # My devices endpoint
    path('my-devices/', MyDevicesAPIView.as_view(), name='my-devices'),
]

"""
COMPLETE POS API ENDPOINTS
===========================

DEVICE MANAGEMENT (Admin):
--------------------------
GET    /api/pos/devices/                           - List devices (read-only)
GET    /api/pos/devices/{id}/                      - Get device details (read-only)
GET    /api/pos/devices/manage/                    - List devices (full access)
POST   /api/pos/devices/manage/                    - Create device
GET    /api/pos/devices/manage/{id}/               - Get device details
PUT    /api/pos/devices/manage/{id}/               - Update device
DELETE /api/pos/devices/manage/{id}/               - Delete device
POST   /api/pos/devices/manage/{id}/activate/      - Activate device
POST   /api/pos/devices/manage/{id}/deactivate/    - Deactivate device
POST   /api/pos/devices/manage/{id}/ping/          - Update device status
POST   /api/pos/devices/manage/{id}/generate_token/ - Generate auth token
GET    /api/pos/devices/manage/online/             - Get online devices
GET    /api/pos/my-devices/                        - Get user's accessible devices


DEVICE AUTHENTICATION:
---------------------
POST   /api/pos/tenants/{tenant_id}/devices/{device_id}/login/
       - Login to device (supports 3 modes)
       
POST   /api/pos/tenants/{tenant_id}/devices/{device_id}/logout/
       - Logout device (requires X-POS-Token)
       
GET    /api/pos/tenants/{tenant_id}/devices/{device_id}/status/
       - Get device status
       
POST   /api/pos/tenants/{tenant_id}/devices/{device_id}/heartbeat/
       - Send heartbeat (requires X-POS-Token)


PORTAL ENDPOINTS (POS Interface):
---------------------------------
GET    /api/pos/portal/                            - Portal menu/products
       (See portal_views.py for detailed endpoints)


DEVICE LOGIN - 3 AUTHENTICATION MODES:
=======================================

MODE 1: User Login (with username & password)
----------------------------------------------
POST /api/pos/tenants/1/devices/POS-001/login/
{
    "username": "cashier@example.com",
    "password": "password123",
    "pin": "1234"  // Optional
}

Response:
{
    "success": true,
    "token": "drf-token-for-user",      // DRF token for API calls
    "device_token": "POS-abc123",       // Device token
    "user": {
        "id": 5,
        "email": "cashier@example.com",
        "name": "John Cashier",
        "role": "cashier",
        "tenant_id": 1
    },
    "device": {...},
    "branch": {...},
    "tenant": {...},
    "session": {
        "logged_in_at": "2024-01-30T12:00:00Z",
        "expires_at": "2024-01-30T20:00:00Z",
        "session_duration_hours": 8
    },
    "redirect_url": "https://tenant.com/devices/POS-001/"
}


MODE 2: Device Credentials (device_id + auth_token)
---------------------------------------------------
POST /api/pos/tenants/1/devices/POS-001/login/
{
    "device_id": "POS-001",
    "auth_token": "POS-abc123xyz",
    "pin": "1234"  // Optional
}

Response:
{
    "success": true,
    "device_token": "POS-abc123xyz",
    "device": {...},
    "branch": {...},
    "tenant": {...},
    "session": {...},
    "redirect_url": "..."
}


MODE 3: Simple Device Login (no credentials - kiosk mode)
---------------------------------------------------------
POST /api/pos/tenants/1/devices/POS-001/login/
{
    "pin": "1234"  // Optional
}

Response:
{
    "success": true,
    "device_token": "POS-abc123xyz",
    "device": {...},
    "branch": {...},
    "tenant": {...},
    "session": {...}
}


USING THE DEVICE TOKEN:
=======================

After login, use the device_token for all subsequent requests:

GET /api/pos/portal/products/
Headers:
X-POS-Token: POS-abc123xyz

POST /api/pos/tenants/1/devices/POS-001/heartbeat/
Headers:
X-POS-Token: POS-abc123xyz


ERROR RESPONSES:
================

Device Not Found:
{
    "success": false,
    "error": "Device not found or inactive",
    "code": "DEVICE_NOT_FOUND"
}

Device Suspended:
{
    "success": false,
    "error": "Device is suspended. Contact administrator.",
    "code": "DEVICE_SUSPENDED"
}

Invalid PIN:
{
    "success": false,
    "error": "Invalid PIN",
    "code": "INVALID_PIN"
}

Invalid Credentials:
{
    "success": false,
    "error": "Invalid credentials",
    "code": "INVALID_CREDENTIALS"
}

Not Authorized:
{
    "success": false,
    "error": "Not authorized for this device",
    "code": "NOT_AUTHORIZED"
}

Tenant Mismatch:
{
    "success": false,
    "error": "Device does not belong to this tenant",
    "code": "TENANT_MISMATCH"
}


INTEGRATION NOTES:
==================

1. Your existing DeviceLoginAPIView has been enhanced with:
   - Support for 3 authentication modes
   - Better error handling with error codes
   - Session expiry tracking
   - IP address logging
   - Proper tenant validation

2. Added new endpoints:
   - logout: Set device offline
   - status: Check device status
   - heartbeat: Keep device online

3. All existing functionality preserved:
   - POSDeviceViewSet (management)
   - DeviceViewSet (read-only)
   - MyDevicesAPIView (user's devices)
   - POSPortalMenuViewSet (portal interface)

4. Your existing permissions and access controls remain intact:
   - IsTenantOwnerOrBranchStaffOrAssigned
   - Role-based queryset filtering
   - Tenant isolation
"""
