# from django.urls import path
# from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import TokenRefreshView

# from apps.users.views import UserViewSet


# # Create router
# router = DefaultRouter()
# router.register(r'users', UserViewSet, basename='user')

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
#     # API endpoints
#     path('api/', include(router.urls)),
    
#     # JWT token refresh
#     path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
# ]