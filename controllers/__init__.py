"""
Módulo de controladores de la aplicación
Incluye controladores para hardware, comunicaciones y seguridad
"""

from .app_controller import App
from .security_controller import SecurityController

# Importar el nuevo SecurityController
try:
    from .security_controller import SecurityController

    SECURITY_CONTROLLER_AVAILABLE = True
except ImportError:
    SECURITY_CONTROLLER_AVAILABLE = False
    print("⚠️ SecurityController no disponible")

# Importar event_handler para compatibilidad
try:
    from .event_handler import DeviceEventHandler

    EVENT_HANDLER_AVAILABLE = True
except ImportError:
    EVENT_HANDLER_AVAILABLE = False
    print("⚠️ DeviceEventHandler no disponible")

# Importar hardware_messages para compatibilidad
try:
    from .hardware_messages import HardwareMessageGenerator, get_message_generator

    HARDWARE_MESSAGES_AVAILABLE = True
except ImportError:
    HARDWARE_MESSAGES_AVAILABLE = False
    print("⚠️ HardwareMessageGenerator no disponible")

# Lista inicial de módulos disponibles
__all__ = ['App']

# Agregar SecurityController si está disponible
if SECURITY_CONTROLLER_AVAILABLE:
    __all__.append('SecurityController')

# Agregar event_handler si está disponible
if EVENT_HANDLER_AVAILABLE:
    __all__.append('DeviceEventHandler')

# Agregar hardware_messages si está disponible
if HARDWARE_MESSAGES_AVAILABLE:
    __all__.extend(['HardwareMessageGenerator', 'get_message_generator'])

# Importar módulos de hardware y comunicaciones solo si están disponibles
try:
    from .device_listener import DeviceListener
    from .BotMesajes import TelegramBot
    from .serial_comm import SerialCommunicator, get_serial_communicator, init_serial, close_serial

    # Agregar al __all__
    __all__.extend(['DeviceListener', 'TelegramBot', 'SerialCommunicator',
                    'get_serial_communicator', 'init_serial', 'close_serial'])

    # Importar telegram_integration si está disponible
    try:
        from .telegram_integration import TelegramDeviceIntegration, get_integration, start_integration, \
            stop_integration

        __all__.extend(['TelegramDeviceIntegration', 'get_integration',
                        'start_integration', 'stop_integration'])
    except ImportError:
        print("⚠️ TelegramDeviceIntegration no disponible")

    print("✅ Módulos de hardware y comunicaciones disponibles")

except ImportError as e:
    print(f"⚠️ Algunos controladores no disponibles: {e}")

    # Intentar importaciones individuales para mejor diagnóstico
    try:
        from .device_listener import DeviceListener

        __all__.append('DeviceListener')
        print("✅ DeviceListener disponible")
    except ImportError:
        print("❌ DeviceListener no disponible (posiblemente falta pyserial)")

    try:
        from .BotMesajes import TelegramBot

        __all__.append('TelegramBot')
        print("✅ TelegramBot disponible")
    except ImportError:
        print("❌ TelegramBot no disponible (posiblemente falta requests)")

    try:
        from .serial_comm import SerialCommunicator, get_serial_communicator, init_serial, close_serial

        __all__.extend(['SerialCommunicator', 'get_serial_communicator', 'init_serial', 'close_serial'])
        print("✅ SerialCommunicator disponible")
    except ImportError:
        print("❌ SerialCommunicator no disponible")

# Imprimir resumen de módulos disponibles
print(f"Módulos disponibles: {', '.join(__all__)}")
