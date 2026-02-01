from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import POSDeviceViewSet, DeviceViewSet
from .portal_views import POSPortalMenuViewSet

router = DefaultRouter()
# Public read-only device endpoints
router.register(r'devices', DeviceViewSet, basename='device')
# Full management endpoints kept under a separate prefix to avoid breaking existing usage
router.register(r'devices/manage', POSDeviceViewSet, basename='pos-device')
router.register(r'portal', POSPortalMenuViewSet, basename='pos-portal')

urlpatterns = [
    path('', include(router.urls)),
]