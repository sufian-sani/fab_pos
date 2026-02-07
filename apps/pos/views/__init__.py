from .views import (
    DeviceViewSet,
    DeviceStatusAPIView,
)


from .base import BasePosDeviceAPIView
from .status import PosDeviceStatusMixin
# from .orders import PosDeviceOrderAPIView
# from .auth import PosDeviceAuthAPIView


__all__ = [ 
    "DeviceViewSet",
    "DeviceStatusAPIView", 
]

class PosDeviceAPIView(
    PosDeviceStatusMixin,
    BasePosDeviceAPIView,
):
    pass
