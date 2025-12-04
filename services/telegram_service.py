"""
Servicio de notificaciones Telegram
Encapsula toda la lógica de envío de mensajes
"""

try:
    from controllers.BotMesajes import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class TelegramService:
    """
    Servicio que maneja notificaciones por Telegram.
    """
    
    def __init__(self, bot_token):
        self.bot = None
        self.available = TELEGRAM_AVAILABLE
        
        if not TELEGRAM_AVAILABLE:
            print("⚠️ TelegramBot no disponible")
            return
        
        try:
            self.bot = TelegramBot(bot_token)
            
            # Verificar conexión
            bot_info = self.bot.get_me()
            if bot_info.get('ok'):
                bot_name = bot_info['result']['first_name']
                print(f"✅ Bot de Telegram conectado: {bot_name}")
            else:
                print("⚠️ Error verificando bot de Telegram")
                self.bot = None
                self.available = False
        except Exception as e:
            print(f"❌ Error iniciando bot de Telegram: {e}")
            self.bot = None
            self.available = False
    
    def is_connected(self):
        """Verifica si el bot está disponible"""
        return self.available and self.bot is not None
    
    def send_alert(self, user_email, title, message):
        """
        Envía una alerta al usuario.
        
        Args:
            user_email: str - Email del usuario
            title: str - Título de la alerta
            message: str - Mensaje de la alerta
        
        Returns:
            tuple (success: bool, result: str)
        """
        if not self.is_connected():
            return False, "Bot de Telegram no disponible"
        
        formatted_message = f"🔔 <b>{title}</b>\n\n{message}"
        return self.bot.send_message_to_user(user_email, formatted_message, parse_mode='HTML')
    
    def send_motion_alert(self, user_email, device_name):
        """Envía alerta de movimiento detectado"""
        return self.send_alert(
            user_email,
            "Sensor de Movimiento",
            f"🚶 Movimiento detectado en {device_name}"
        )
    
    def send_smoke_alert(self, user_email, device_name):
        """Envía alerta de humo detectado"""
        return self.send_alert(
            user_email,
            "Detector de Humo",
            f"💨 Humo detectado en {device_name}"
        )
    
    def send_panic_alert(self, user_email, device_name):
        """Envía alerta de pánico"""
        return self.send_alert(
            user_email,
            "¡ALERTA DE SEGURIDAD!",
            f"🚨 Alarma activada en {device_name}"
        )
    
    def send_door_alert(self, user_email, state):
        """Envía alerta de puerta/ventana"""
        return self.send_alert(
            user_email,
            "Alerta de Acceso",
            f"🚪 Puerta/Ventana {state}"
        )
    
    def send_laser_alert(self, user_email):
        """Envía alerta de perímetro láser interrumpido"""
        return self.send_alert(
            user_email,
            "Alerta de Seguridad",
            "🔴 Perímetro láser INTERRUMPIDO"
        )
    
    def link_user(self, user_email):
        """
        Vincula un usuario con Telegram.
        
        Args:
            user_email: str - Email del usuario
        
        Returns:
            str o None - Chat ID si está vinculado, None si no
        """
        if not self.is_connected():
            return None
        
        # Obtener actualizaciones para vincular
        self.bot.get_updates()
        
        # Retornar chat_id si existe
        return self.bot.get_user_chat_id(user_email)