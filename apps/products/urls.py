# ============================================================================
# apps/pos/urls.py - UPDATED to work with your existing code
# ============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
)

router = DefaultRouter()

# Public read-only device endpoints
router.register(r'', CategoryViewSet, basename='category')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
]