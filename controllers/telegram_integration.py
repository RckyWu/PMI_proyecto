"""
Modulo de integración entre dispositivos hardware y Telegram
Conecta el DeviceListener con el TelegramBot y DeviceEventHandler
"""

import threading
import time
from controllers.device_listener import DeviceListener
from controllers.BotMesajes import TelegramBot
from controllers.event_handler import DeviceEventHandler
from models.user_manager import UserManager
from controllers.hardware_messages import get_message_generator


class TelegramDeviceIntegration:
    """
    Integra la comunicación serial con el bot de Telegram
    """

    def __init__(self, bot_token, serial_port="COM5", baud_rate=115200):
        # Inicializar componentes
        self.user_manager = UserManager()
        self.telegram_bot = TelegramBot(bot_token)
        self.event_handler = DeviceEventHandler(self.user_manager, self.telegram_bot)
        self.message_generator = get_message_generator()

        # Configurar listener de dispositivos
        self.device_listener = DeviceListener(
            puerto=serial_port,
            baud=baud_rate
        )

        # Estado
        self.running = False
        self.processing_thread = None

        # Mapeo de formato mensaje serial -> parametros para event handler
        self.message_parsers = {
            "PIR": self._parse_pir_message,
            "HUMO": self._parse_humo_message,
            "PUERTA": self._parse_puerta_message,
            "LASER": self._parse_laser_message,
            "PANICO": self._parse_panico_message,
            "TEMPERATURA": self._parse_temperatura_message,
            "HUMEDAD": self._parse_humedad_message,
            "VENTANA": self._parse_ventana_message,
            "CERRADURA": self._parse_cerradura_message,
        }

    def start(self):
        """Inicia la integración"""
        if self.running:
            return

        # Iniciar listener de dispositivos
        self.device_listener.start()

        # Iniciar hilo de procesamiento
        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_messages,
            daemon=True
        )
        self.processing_thread.start()

        print(f"Integracion Telegram-Dispositivos iniciada")
        print(f"Puerto serial: {self.device_listener.puerto}")
        print(f"Bot Token: {self.telegram_bot.bot_token[:10]}...")

    def stop(self):
        """Detiene la integración"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2)
        self.device_listener.stop()
        print("Integracion Telegram-Dispositivos detenida")

    def _process_messages(self):
        """Procesa mensajes de dispositivos y envía notificaciones"""
        while self.running:
            try:
                # Obtener mensaje del dispositivo
                message = self.device_listener.queue.get(timeout=0.5)

                # Procesar mensaje
                self._process_device_message(message)

            except Exception as e:
                time.sleep(0.1)

    def _process_device_message(self, raw_message):
        """
        Procesa un mensaje crudo del dispositivo serial
        Formato esperado: DISPOSITIVO:EVENTO:ZONA:DATOS_ADICIONALES
        Ejemplo: PIR:MOTION:SALA_PRINCIPAL:INTENSIDAD=85
        """
        try:
            print(f"Mensaje dispositivo recibido: {raw_message}")

            # Parsear mensaje
            parts = raw_message.split(":", 3)

            if len(parts) < 3:
                print(f"Formato invalido: {raw_message}")
                return

            hardware_id = parts[0].strip()
            event_type = parts[1].strip()
            zone = parts[2].strip()
            data = parts[3].strip() if len(parts) > 3 else ""

            # Verificar si es un dispositivo conocido
            if hardware_id not in self.message_parsers:
                print(f"Dispositivo desconocido: {hardware_id}")
                return

            # Procesar con parser específico
            parsed_data = self.message_parsers[hardware_id](data)

            # Enviar al event handler
            self.event_handler.handle_event(
                hardware_id=hardware_id,
                event_type=event_type,
                zone=zone,
                data=parsed_data
            )

            # Registrar en log
            self._log_event(hardware_id, event_type, zone, data)

        except Exception as e:
            print(f"Error procesando mensaje: {e}")

    def _parse_pir_message(self, data):
        """Parsea mensaje de sensor PIR"""
        if "INTENSIDAD=" in data:
            intensity = data.split("=")[1]
            return f"Intensidad: {intensity}%"
        return data

    def _parse_humo_message(self, data):
        """Parsea mensaje de detector de humo"""
        if "NIVEL=" in data:
            level = data.split("=")[1]
            return f"Nivel de humo: {level}"
        return data

    def _parse_puerta_message(self, data):
        """Parsea mensaje de sensor de puerta"""
        return data

    def _parse_laser_message(self, data):
        """Parsea mensaje de sensor laser"""
        return data

    def _parse_panico_message(self, data):
        """Parsea mensaje de botón de pánico"""
        return "Boton de panico activado"

    def _parse_temperatura_message(self, data):
        """Parsea mensaje de sensor de temperatura"""
        if "VALOR=" in data:
            value = data.split("=")[1]
            return f"Temperatura: {value}°C"
        return data

    def _parse_humedad_message(self, data):
        """Parsea mensaje de sensor de humedad"""
        if "VALOR=" in data:
            value = data.split("=")[1]
            return f"Humedad: {value}%"
        return data

    def _parse_ventana_message(self, data):
        """Parsea mensaje de sensor de ventana"""
        return data

    def _parse_cerradura_message(self, data):
        """Parsea mensaje de cerradura inteligente"""
        return data

    def _log_event(self, hardware_id, event_type, zone, data):
        """Registra evento en archivo de log"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {hardware_id}:{event_type}:{zone}:{data}\n"

        try:
            with open("device_events.log", "a", encoding="utf-8") as f:
                f.write(log_entry)
        except:
            pass

    def test_integration(self):
        """Prueba la integración enviando mensajes de prueba"""
        test_messages = [
            "PIR:MOTION:SALA_PRINCIPAL:INTENSIDAD=85",
            "HUMO:SMOKE:COCINA:NIVEL=ALTO",
            "PUERTA:OPEN:ENTRADA_PRINCIPAL:",
            "PANICO:PANIC:DORMITORIO:URGENTE",
            "TEMPERATURA:TEMPERATURE_HIGH:COCINA:VALOR=42",
        ]

        print("=== PRUEBA DE INTEGRACION ===")
        for msg in test_messages:
            print(f"Enviando mensaje de prueba: {msg}")
            self._process_device_message(msg)
            time.sleep(1)

    def get_status(self):
        """Obtiene estado de la integración"""
        return {
            "running": self.running,
            "serial_connected": hasattr(self.device_listener, 'ser') and self.device_listener.ser,
            "telegram_bot_ready": self.telegram_bot is not None,
            "user_logged_in": bool(self.user_manager.current_user),
            "chat_ids_count": len(self.telegram_bot.chat_ids),
            "emergency_ids_count": len(self.telegram_bot.emergency_chat_ids)
        }


# Singleton para uso global
_integration = None


def get_integration(bot_token=None, serial_port="COM5", baud_rate=115200):
    """Obtiene la instancia única de la integración"""
    global _integration
    if _integration is None and bot_token:
        _integration = TelegramDeviceIntegration(bot_token, serial_port, baud_rate)
    return _integration


def start_integration(bot_token=None, serial_port="COM5", baud_rate=115200):
    """Inicia la integración"""
    integration = get_integration(bot_token, serial_port, baud_rate)
    if integration:
        integration.start()
        return True
    return False


def stop_integration():
    """Detiene la integración"""
    global _integration
    if _integration:
        _integration.stop()
        _integration = None