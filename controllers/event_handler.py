"""
Manejador de eventos de dispositivos hardware
Envía notificaciones a Telegram cuando los dispositivos se activan

"""

from datetime import datetime


class DeviceEventHandler:
    """
    Clase que maneja eventos de dispositivos y envía notificaciones a Telegram

    Regla especial:
    - Botón de pánico → Número de emergencia
    - Otros dispositivos → Número normal del usuario
    """

    def __init__(self, user_manager, telegram_bot):
        self.user_manager = user_manager
        self.telegram_bot = telegram_bot

        # Nombres descriptivos de dispositivos
        self.device_names = {
            "PIR": "Sensor de Movimiento",
            "HUMO": "Detector de Humo",
            "PUERTA": "Sensor de Puerta",
            "LASER": "Sensor Laser",
            "PANICO": "Boton de Panico",
            "PRESENCIA": "Simulador de Presencia",
            "TEMPERATURA": "Sensor de Temperatura",
            "HUMEDAD": "Sensor de Humedad",
            "VENTANA": "Sensor de Ventana",
            "CERRADURA": "Cerradura Inteligente"
        }

        # Descripciones de eventos
        self.event_descriptions = {
            "MOTION": "movimiento detectado",
            "SMOKE": "humo detectado",
            "OPEN": "abierto/a",
            "CLOSE": "cerrado/a",
            "TRIGGER": "activado",
            "PANIC": "presionado",
            "ALARM": "alarma activada",
            "TEMPERATURE_HIGH": "temperatura muy alta",
            "TEMPERATURE_LOW": "temperatura muy baja",
            "HUMIDITY_HIGH": "humedad muy alta",
            "HUMIDITY_LOW": "humedad muy baja",
            "BREAK": "posible rotura",
            "LOCK": "bloqueado",
            "UNLOCK": "desbloqueado",
            "FAILED_ATTEMPT": "intento fallido de acceso"
        }

    def handle_event(self, hardware_id, event_type, zone="Desconocida", data=""):
        """
        Procesa un evento de dispositivo y envía notificación a Telegram

        Args:
            hardware_id (str): ID del dispositivo hardware
            event_type (str): Tipo de evento
            zone (str): Zona donde ocurrió
            data (str): Datos adicionales
        """
        # Verificar que haya usuario activo
        current_user = self.user_manager.current_user
        if not current_user:
            print(f"Evento ignorado: No hay usuario logueado - {hardware_id}:{event_type}")
            return

        # Verificar que el bot de Telegram esté disponible
        if not self.telegram_bot:
            print(f"Evento ignorado: Bot de Telegram no disponible - {hardware_id}:{event_type}")
            return

        # Caso especial: Botón de pánico va al número de emergencia
        if hardware_id == "PANICO" and event_type in ["PANIC", "TRIGGER", "ALARM"]:
            self._handle_panic_event(zone, data, current_user)
            return

        # Para otros dispositivos: enviar al número normal
        self._handle_normal_event(hardware_id, event_type, zone, data, current_user)

    def _handle_panic_event(self, zone, data, current_user):
        """Maneja evento de botón de pánico (envía al número de emergencia)"""
        print(f"EVENTO DE PANICO detectado")

        # Obtener perfil del usuario
        profile = self.user_manager.get_current_user_profile()
        if not profile:
            print(f"ERROR: No se pudo obtener perfil para {current_user}")
            return

        # Verificar que haya número de emergencia configurado
        emergency_chat_id = profile.get('emergency_chat_id')
        if not emergency_chat_id:
            print(f"ERROR: No hay número de emergencia configurado para {current_user}")
            return

        # Crear mensaje de pánico
        message = self._create_panic_message(zone, current_user, data)

        # Enviar al número de emergencia
        success, result = self.telegram_bot.send_message(
            emergency_chat_id,
            message,
            parse_mode='HTML'
        )

        if success:
            print(f"Alerta de pánico enviada al número de emergencia")
        else:
            print(f"Error enviando alerta de pánico: {result}")

    def _handle_normal_event(self, hardware_id, event_type, zone, data, current_user):
        """Maneja eventos normales (envía al número principal del usuario)"""
        # Verificar que el usuario tenga chat_id configurado
        chat_id = self.telegram_bot.chat_ids.get(current_user)
        if not chat_id:
            print(f"Evento ignorado: Usuario no tiene chat_id - {current_user}")
            return

        # Generar y enviar mensaje
        message = self._create_normal_message(hardware_id, event_type, zone, data)

        success, result = self.telegram_bot.send_message(
            chat_id,
            message,
            parse_mode='HTML'
        )

        if success:
            print(f"Notificacion enviada a {current_user} - {hardware_id}:{event_type}")
        else:
            print(f"Error enviando notificacion: {result}")

    def _create_panic_message(self, zone, user_email, data=""):
        """Crea mensaje para botón de pánico"""
        timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

        message = f"""🚨 <b>EMERGENCIA - BOTON DE PANICO ACTIVADO</b>

⚠️ <b>Se requiere asistencia inmediata</b>

<b>Informacion:</b>
• Tipo: Botón de Pánico
• Zona: {zone}
• Usuario: {user_email}
• Hora: {timestamp}"""

        if data:
            message += f"\n• Datos: {data}"

        message += "\n\n<b>☎️ Contactar al usuario inmediatamente</b>"

        return message

    def _create_normal_message(self, hardware_id, event_type, zone, data=""):
        """Crea mensaje normal para notificaciones"""
        device_name = self.device_names.get(hardware_id, hardware_id)
        event_desc = self.event_descriptions.get(event_type, "activado")
        timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

        # Crear mensaje básico
        message = f"""🔔 <b>Notificacion del Sistema</b>

<b>Dispositivo:</b> {device_name}
<b>Evento:</b> {event_desc}
<b>Zona:</b> {zone}
<b>Hora:</b> {timestamp}"""

        # Agregar datos adicionales si existen
        if data:
            message += f"\n<b>Informacion adicional:</b> {data}"

        return message
