from .views import (
    POSDeviceViewSet, 
    DeviceViewSet, 
    DeviceLogoutAPIView, 
    MyDevicesAPIView, 
    DeviceHeartbeatAPIView, 
    DeviceStatusAPIView,
)


from .base import BasePosDeviceAPIView
from .status import PosDeviceStatusMixin
# from .orders import PosDeviceOrderAPIView
# from .auth import PosDeviceAuthAPIView


__all__ = [ 
    "POSDeviceViewSet", 
    "DeviceViewSet", 
    "DeviceLogoutAPIView", 
    "MyDevicesAPIView", 
    "DeviceHeartbeatAPIView", 
    "DeviceStatusAPIView", 
]

class PosDeviceAPIView(
    PosDeviceStatusMixin,
    BasePosDeviceAPIView,
    # PosDeviceStatusAPIView,
):
    pass
