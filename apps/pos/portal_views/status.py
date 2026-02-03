from rest_framework.decorators import action
from rest_framework.response import Response
from .views import PosDeviceAPIView as BasePosDeviceAPIView

class PosDeviceStatusAPIView(BasePosDeviceAPIView):
    """Extend the base ViewSet to add new actions"""

    @action(detail=True, methods=['get'], url_path='check_status')
    def check_status(self, request, tenant_id=None, device_id=None):
        # breakpoint() can be used for debugging
        return Response({
            "success": True,
            "message": "Device is online",
            "device_id": device_id
        })