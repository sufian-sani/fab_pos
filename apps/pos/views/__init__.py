from .views import (
    DeviceViewSet,
    DeviceStatusAPIView,
)


from .base import BasePosDeviceAPIView
from .status import PosDeviceStatusMixin
from .products import PosDeviceProductsMixin
# from .orders import PosDeviceOrderAPIView
# from .auth import PosDeviceAuthAPIView

class PosDeviceAPIView(
    PosDeviceStatusMixin,
    PosDeviceProductsMixin,
    BasePosDeviceAPIView,
):
    pass

__all__ = [ 
    "DeviceViewSet",
    "DeviceStatusAPIView",
    'PosDeviceAPIView',
]
