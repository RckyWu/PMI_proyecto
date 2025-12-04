"""
Modulo de vistas de la aplicacion
"""

from .splash_screen import SplashScreen
from .login_screen import LoginScreen
from .register_screen import RegisterScreen
from .device_widget import DeviceWidget
from .add_device_frame import AddDeviceFrame
from .devices_frame import DevicesFrame
from .device_detail_window import DeviceDetailWindow
from .telegram_link_frame import TelegramLinkFrame
from .main_menu import MainMenu

__all__ = [
    'SplashScreen',
    'LoginScreen',
    'RegisterScreen',
    'DeviceWidget',
    'AddDeviceFrame',
    'DevicesFrame',
    'DeviceDetailWindow',
    'TelegramLinkFrame',
    'MainMenu'
]
