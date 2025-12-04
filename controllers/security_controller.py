"""
Controlador de seguridad
Coordina los servicios y maneja la lógica de negocio de eventos de seguridad
"""

from services import SerialService, EventService, TelegramService


class SecurityController:
    """
    Controlador que coordina la respuesta a eventos de seguridad.
    Orquesta los servicios de serial, eventos y notificaciones.
    """

    def __init__(self, user_manager, telegram_token):
        self.user_manager = user_manager

        # Inicializar servicios
        self.serial_service = SerialService()
        self.event_service = EventService()
        self.telegram_service = TelegramService(telegram_token)

        # Callbacks de UI
        self.on_event_callback = None
        self.on_alert_callback = None

    def set_event_callback(self, callback):
        """
        Establece callback para cuando hay un nuevo evento.

        Args:
            callback: function(event) - Función que recibe el evento estructurado
        """
        self.on_event_callback = callback

    def set_alert_callback(self, callback):
        """
        Establece callback para mostrar alertas visuales.

        Args:
            callback: function(title, message) - Función que muestra la alerta
        """
        self.on_alert_callback = callback
    def process_hardware_messages(self):
        """
        Procesa mensajes del hardware.
        Debe llamarse periódicamente desde la UI.
        Returns:
            list - Lista de eventos procesados
        """
        if not self.serial_service.is_connected():
            return []

        events = []

        # Procesar todos los mensajes disponibles
        while True:
            raw_message = self.serial_service.get_event()

            if not raw_message:
                break

            # Parsear evento
            event = self.event_service.parse_event(raw_message)

            if not event:
                continue

            events.append(event)

            # Manejar evento
            self._handle_event(event)

        return events

    def _handle_event(self, event):
        """Maneja un evento estructurado"""
        print(f"📨 Evento: {event['type']} - {event['message']}")

        # Notificar a la UI
        if self.on_event_callback:
            self.on_event_callback(event)

        # Enviar notificación por Telegram si corresponde
        if self.event_service.should_notify(event):
            self._send_telegram_notification(event)

        # Mostrar alerta visual si corresponde
        if self.event_service.should_show_alert(event):
            self._show_visual_alert(event)

    def _send_telegram_notification(self, event):
        """Envía notificación por Telegram"""
        if not self.telegram_service.is_connected():
            return

        user_email = self.user_manager.current_user
        if not user_email:
            return

        event_type = event['type']
        device_name = event['device']

        # Enviar según tipo de evento
        if event_type == 'motion':
            self.telegram_service.send_motion_alert(user_email, device_name)
        elif event_type == 'smoke':
            self.telegram_service.send_smoke_alert(user_email, device_name)
        elif event_type == 'panic':
            self.telegram_service.send_panic_alert(user_email, device_name)
        elif event_type == 'door':
            self.telegram_service.send_door_alert(user_email, event['state'])
        elif event_type == 'laser':
            self.telegram_service.send_laser_alert(user_email)
    def _show_visual_alert(self, event):
        """Muestra alerta visual en la UI"""
        if self.on_alert_callback:
            title = event['device']
            message = event['message']
            self.on_alert_callback(title, message)

    def activate_device(self, device):
        """
        Activa un dispositivo.

        Args:
            device: dict - Dispositivo con campos 'id', 'tipo', etc.

        Returns:
            tuple (success: bool, message: str)
        """
        device_type = device.get('tipo', '')

        success = self.serial_service.activate_device(device_type)

        if success:
            message = "Dispositivo activado - Comando enviado al hardware"
        else:
            message = "Error: No se pudo enviar el comando"

        return success, message

    def deactivate_device(self, device):
        """
        Desactiva un dispositivo.

        Args:
            device: dict - Dispositivo con campos 'id', 'tipo', etc.

        Returns:
            tuple (success: bool, message: str)
        """
        device_type = device.get('tipo', '')

        success = self.serial_service.deactivate_device(device_type)

        if success:
            message = "Dispositivo desactivado - Comando enviado al hardware"
        else:
            message = "Error: No se pudo enviar el comando"

        return success, message

    def open_lock(self):
        """Abre la cerradura"""
        success = self.serial_service.open_lock()
        return success, "Cerradura abierta" if success else "Error abriendo cerradura"
    def close_lock(self):
        """Cierra la cerradura"""
        success = self.serial_service.close_lock()
        return success, "Cerradura cerrada" if success else "Error cerrando cerradura"

    def link_telegram_account(self):
        """
        Vincula la cuenta actual con Telegram.

        Returns:
            tuple (success: bool, message: str, chat_id: str o None)
        """
        if not self.telegram_service.is_connected():
            return False, "Bot de Telegram no disponible", None

        user_email = self.user_manager.current_user
        if not user_email:
            return False, "No hay usuario activo", None

        chat_id = self.telegram_service.link_user(user_email)

        if chat_id:
            return True, f"Cuenta vinculada. Chat ID: {chat_id}", chat_id
        else:
            return False, "No se encontró chat_id. Envía un mensaje al bot primero.", None

    def get_connection_status(self):
        """
        Retorna el estado de las conexiones.

        Returns:
            dict con keys 'serial' y 'telegram' (valores bool)
        """
        return {
            'serial': self.serial_service.is_connected(),
            'telegram': self.telegram_service.is_connected()
        }