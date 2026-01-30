from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import POSDeviceViewSet

router = DefaultRouter()
router.register(r'devices', POSDeviceViewSet, basename='pos-device')

urlpatterns = [
    path('', include(router.urls)),
]