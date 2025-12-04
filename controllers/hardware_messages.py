"""
Modulo para crear mensajes personalizados para dispositivos hardware
Mapea eventos de hardware a mensajes descriptivos para notificaciones
"""

import time
from datetime import datetime


class HardwareMessageGenerator:
    """
    Genera mensajes personalizados para cada tipo de dispositivo hardware.
    Conecta IDs de hardware con mensajes descriptivos para notificaciones.
    """

    def __init__(self):
        # Mapeo de IDs de hardware a nombres descriptivos
        self.hardware_names = {
            "PIR": "Sensor de Movimiento PIR",
            "HUMO": "Detector de Humo",
            "PUERTA": "Sensor de Puerta",
            "LASER": "Sensor Laser de Seguridad",
            "PANICO": "Boton de Panico",
            "PRESENCIA": "Simulador de Presencia",
            "TEMPERATURA": "Sensor de Temperatura",
            "HUMEDAD": "Sensor de Humedad",
            "VENTANA": "Sensor de Ventana",
            "CERRADURA": "Cerradura Inteligente"
        }

        # Mapeo de tipos de eventos a mensajes base
        self.event_messages = {
            "MOTION": "movimiento detectado",
            "SMOKE": "niveles de humo altos detectados",
            "OPEN": "abierto/a",
            "CLOSE": "cerrado/a",
            "TRIGGER": "activado",
            "ALARM": "alarma activada",
            "PANIC": "boton de panico presionado",
            "TAMPER": "intento de manipulacion",
            "LOW_BATTERY": "bateria baja",
            "ONLINE": "dispositivo conectado",
            "OFFLINE": "dispositivo desconectado",
            "TEMPERATURE_HIGH": "temperatura muy alta",
            "TEMPERATURE_LOW": "temperatura muy baja",
            "HUMIDITY_HIGH": "humedad muy alta",
            "HUMIDITY_LOW": "humedad muy baja"
        }

        # Mensajes personalizados por combinación dispositivo+evento
        self.custom_messages = {
            # Sensor PIR
            ("PIR", "MOTION"): "Movimiento detectado! Revisa el area.",
            ("PIR", "TAMPER"): "Posible manipulacion del sensor de movimiento.",

            # Detector de Humo
            ("HUMO", "SMOKE"): "ALERTA DE HUMO! Posible incendio.",
            ("HUMO", "ALARM"): "Alarma de humo activada. Verificar inmediatamente.",

            # Sensor de Puerta
            ("PUERTA", "OPEN"): "Puerta abierta fuera de horario.",
            ("PUERTA", "CLOSE"): "Puerta cerrada correctamente.",

            # Sensor Laser
            ("LASER", "TRIGGER"): "Barrera laser interrumpida! Posible intrusion.",
            ("LASER", "TAMPER"): "Intento de manipulacion de sensor laser.",

            # Botón de Pánico
            ("PANICO", "PANIC"): "EMERGENCIA! Boton de panico activado.",
            ("PANICO", "TRIGGER"): "Solicitud de ayuda inmediata.",

            # Simulador de Presencia
            ("PRESENCIA", "ON"): "Simulador de presencia activado.",
            ("PRESENCIA", "OFF"): "Simulador de presencia desactivado.",

            # Sensor de Temperatura
            ("TEMPERATURA", "TEMPERATURE_HIGH"): "Temperatura critica alta!",
            ("TEMPERATURA", "TEMPERATURE_LOW"): "Temperatura critica baja!",

            # Sensor de Humedad
            ("HUMEDAD", "HUMIDITY_HIGH"): "Humedad excesiva detectada!",
            ("HUMEDAD", "HUMIDITY_LOW"): "Humedad muy baja detectada!",

            # Sensor de Ventana
            ("VENTANA", "OPEN"): "Ventana abierta inesperadamente.",
            ("VENTANA", "BREAK"): "Posible rotura de ventana!",

            # Cerradura Inteligente
            ("CERRADURA", "LOCK"): "Cerradura bloqueada.",
            ("CERRADURA", "UNLOCK"): "Cerradura desbloqueada.",
            ("CERRADURA", "FAILED_ATTEMPT"): "Intento fallido de apertura."
        }

        # Niveles de prioridad (1=Crítico, 2=Alto, 3=Medio, 4=Bajo)
        self.priority_levels = {
            "PANIC": 1,
            "SMOKE": 1,
            "ALARM": 1,
            "BREAK": 1,
            "MOTION": 2,
            "TRIGGER": 2,
            "TEMPERATURE_HIGH": 2,
            "TEMPERATURE_LOW": 2,
            "OPEN": 3,
            "CLOSE": 3,
            "TAMPER": 3,
            "FAILED_ATTEMPT": 3,
            "LOW_BATTERY": 4,
            "ONLINE": 4,
            "OFFLINE": 4
        }

    def generate_message(self, hardware_id, event_type, zone="Desconocida", data=""):
        """
        Genera un mensaje personalizado para un evento de hardware.

        Args:
            hardware_id (str): ID del dispositivo hardware (ej: "PIR", "HUMO")
            event_type (str): Tipo de evento (ej: "MOTION", "SMOKE")
            zone (str): Zona donde ocurrió el evento
            data (str): Información adicional del hardware

        Returns:
            dict: Mensaje formateado con campos:
                - title: Título del mensaje
                - body: Cuerpo descriptivo
                - priority: Nivel de prioridad (1-4)
                - timestamp: Hora del evento
                - raw_data: Datos originales del hardware
        """
        # Obtener nombre descriptivo del dispositivo
        device_name = self.hardware_names.get(hardware_id, hardware_id)

        # Obtener mensaje personalizado o generar uno genérico
        custom_key = (hardware_id, event_type)
        if custom_key in self.custom_messages:
            message_body = self.custom_messages[custom_key]
        else:
            event_desc = self.event_messages.get(event_type, "evento detectado")
            message_body = f"{device_name}: {event_desc}"

        # Crear título según prioridad
        priority = self.priority_levels.get(event_type, 3)

        if priority == 1:
            title = f"EMERGENCIA - {device_name}"
        elif priority == 2:
            title = f"ALERTA - {device_name}"
        elif priority == 3:
            title = f"NOTIFICACION - {device_name}"
        else:
            title = f"INFORMACION - {device_name}"

        # Formatear zona y datos adicionales
        zone_info = f" en {zone}" if zone != "Desconocida" else ""
        data_info = f"\nDatos: {data}" if data else ""

        # Crear cuerpo completo del mensaje
        full_body = f"{message_body}{zone_info}\n"
        full_body += f"Dispositivo: {device_name}\n"
        full_body += f"Hora: {datetime.now().strftime('%H:%M:%S')}\n"
        full_body += f"Fecha: {datetime.now().strftime('%d/%m/%Y')}{data_info}"

        return {
            "title": title,
            "body": full_body,
            "priority": priority,
            "device_id": hardware_id,
            "device_name": device_name,
            "event_type": event_type,
            "zone": zone,
            "timestamp": datetime.now().isoformat(),
            "raw_data": f"{hardware_id}:{event_type}:{zone}:{data}" if data else f"{hardware_id}:{event_type}:{zone}"
        }

    def generate_telegram_message(self, hardware_id, event_type, zone="Desconocida", data=""):
        """
        Genera mensaje formateado específicamente para Telegram.

        Returns:
            str: Mensaje listo para enviar por Telegram
        """
        msg_data = self.generate_message(hardware_id, event_type, zone, data)

        # Formatear para Telegram con HTML
        telegram_msg = f"<b>{msg_data['title']}</b>\n\n"
        telegram_msg += f"{msg_data['body']}\n\n"

        # Agregar texto según prioridad
        if msg_data['priority'] == 1:
            telegram_msg += "URGENTE - Requiere accion inmediata"
        elif msg_data['priority'] == 2:
            telegram_msg += "ALERTA - Revisar pronto"
        elif msg_data['priority'] == 3:
            telegram_msg += "Notificacion informativa"
        else:
            telegram_msg += "Informacion del sistema"

        return telegram_msg

    def get_device_info(self, hardware_id):
        """
        Obtiene información descriptiva de un dispositivo hardware.

        Returns:
            dict: Información del dispositivo o None si no existe
        """
        device_info = {
            "PIR": {
                "name": "Sensor de Movimiento PIR",
                "description": "Detector de movimiento por infrarrojos pasivo",
                "location_hint": "Instalar en esquinas a 2m de altura",
                "normal_events": ["MOTION", "TAMPER", "LOW_BATTERY"]
            },
            "HUMO": {
                "name": "Detector de Humo",
                "description": "Sensor optico de particulas de humo",
                "location_hint": "Instalar en techo, lejos de cocinas",
                "normal_events": ["SMOKE", "ALARM", "LOW_BATTERY"]
            },
            "PUERTA": {
                "name": "Sensor de Puerta Magnetico",
                "description": "Sensor de contacto para puertas",
                "location_hint": "Instalar en marco y hoja de puerta",
                "normal_events": ["OPEN", "CLOSE", "TAMPER"]
            },
            "LASER": {
                "name": "Sensor Laser de Seguridad",
                "description": "Barrera laser invisible",
                "location_hint": "Alinear emisor y receptor",
                "normal_events": ["TRIGGER", "TAMPER", "OFFLINE"]
            },
            "PANICO": {
                "name": "Boton de Panico",
                "description": "Dispositivo para emergencias",
                "location_hint": "Instalar en ubicaciones discretas pero accesibles",
                "normal_events": ["PANIC", "TRIGGER"]
            },
            "PRESENCIA": {
                "name": "Simulador de Presencia",
                "description": "Activa luces/electrodomesticos automaticamente",
                "location_hint": "Conectar a lamparas o televisores",
                "normal_events": ["ON", "OFF", "SCHEDULE_START", "SCHEDULE_END"]
            },
            "TEMPERATURA": {
                "name": "Sensor de Temperatura",
                "description": "Monitor de temperatura ambiental",
                "location_hint": "Evitar fuentes directas de calor/frio",
                "normal_events": ["TEMPERATURE_HIGH", "TEMPERATURE_LOW", "NORMAL"]
            },
            "HUMEDAD": {
                "name": "Sensor de Humedad",
                "description": "Monitor de humedad relativa",
                "location_hint": "Ideal para banos, sotanos, cocinas",
                "normal_events": ["HUMIDITY_HIGH", "HUMIDITY_LOW", "NORMAL"]
            },
            "VENTANA": {
                "name": "Sensor de Ventana",
                "description": "Detector de apertura/rotura de ventanas",
                "location_hint": "Instalar en marco de ventana",
                "normal_events": ["OPEN", "CLOSE", "BREAK", "VIBRATION"]
            },
            "CERRADURA": {
                "name": "Cerradura Inteligente",
                "description": "Cerradura electronica controlable remotamente",
                "location_hint": "Requiere instalacion profesional",
                "normal_events": ["LOCK", "UNLOCK", "FAILED_ATTEMPT", "JAMMED"]
            }
        }

        return device_info.get(hardware_id)

    def get_all_devices_info(self):
        """Retorna información de todos los dispositivos hardware soportados"""
        return [self.get_device_info(hid) for hid in self.hardware_names.keys()
                if self.get_device_info(hid) is not None]


# Singleton para uso global
_hardware_message_generator = None


def get_message_generator():
    """Obtiene la instancia única del generador de mensajes"""
    global _hardware_message_generator
    if _hardware_message_generator is None:
        _hardware_message_generator = HardwareMessageGenerator()
    return _hardware_message_generator