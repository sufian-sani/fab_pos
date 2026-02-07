# ============================================================================
# apps/pos/urls.py - UPDATED to work with your existing code
# ============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet,
    DeviceStatusAPIView,
    PosDeviceAPIView,
)

router = DefaultRouter()

# Public read-only device endpoints
router.register(r'devices', DeviceViewSet, basename='device')

router.register(r'tenants/(?P<tenant_id>\d+)/device', PosDeviceAPIView, basename='tenant-device')


urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    path(
        'tenants/<int:tenant_id>/devices/<str:device_id>/status/',
        DeviceStatusAPIView.as_view(),
        name='device-status'
    ),
]
