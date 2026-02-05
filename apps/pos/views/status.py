from rest_framework.decorators import action
from rest_framework.response import Response
from .base import BasePosDeviceAPIView

class PosDeviceStatusMixin:

    @action(detail=True, methods=["get"], url_path="check_status")
    def check_status(self, request, *args, **kwargs):
        device = self.get_object()

        return Response({
            "success": True,
            "device_id": device.device_id,
            "status": device.status,
            "is_online": device.is_online,
            "last_seen": device.last_seen,
        })

    @action(detail=True, methods=["get"], url_path="test")
    def test(self, request, *args, **kwargs):
        device = self.get_object()

        return Response({
            "test": "test response",
        })
