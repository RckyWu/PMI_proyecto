"""
Módulo de controladores de la aplicación
"""

from .app_controller import App
from .security_controller import SecurityController

# Importar device_listener solo si está disponible
try:
    from .device_listener import DeviceListener
    __all__ = ['App', 'DeviceListener', 'SecurityController']
except ImportError:
    __all__ = ['App', 'SecurityController']
    print("⚠️ DeviceListener no disponible (falta pyserial)")

# Importar BotMesajes solo si está disponible
try:
    from .BotMesajes import TelegramBot
    if 'DeviceListener' in __all__:
        __all__ = ['App', 'DeviceListener', 'TelegramBot', 'SecurityController']
    else:
        __all__ = ['App', 'TelegramBot', 'SecurityController']
except ImportError:
    print("⚠️ TelegramBot no disponible (falta requests)")