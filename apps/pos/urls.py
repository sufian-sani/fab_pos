from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import POSDeviceViewSet, DeviceViewSet, DeviceLoginAPIView, MyDevicesAPIView
from .portal_views import POSPortalMenuViewSet

router = DefaultRouter()
# Public read-only device endpoints
router.register(r'devices', DeviceViewSet, basename='device')
# Full management endpoints kept under a separate prefix to avoid breaking existing usage
router.register(r'devices/manage', POSDeviceViewSet, basename='pos-device')
router.register(r'portal', POSPortalMenuViewSet, basename='pos-portal')

urlpatterns = [
    path('', include(router.urls)),
    path('tenants/<int:tenant_id>/devices/<str:device_id>/login/', DeviceLoginAPIView.as_view(), name='device-login'),
    path('my-devices/', MyDevicesAPIView.as_view(), name='my-devices'),
]