from rest_framework.decorators import action
from rest_framework.response import Response
# from .base import BasePosDeviceAPIView

class PosDeviceProductsMixin:

    @action(detail=True, methods=["get"], url_path="products")
    def products(self, request, *args, **kwargs):
        device = self.get_object()

        return Response({
            "check_product": "check_product",
        })
