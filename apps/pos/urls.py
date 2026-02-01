from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import POSDeviceViewSet
from .portal_views import POSPortalMenuViewSet

router = DefaultRouter()
router.register(r'devices', POSDeviceViewSet, basename='pos-device')
router.register(r'portal', POSPortalMenuViewSet, basename='pos-portal')

urlpatterns = [
    path('', include(router.urls)),
]