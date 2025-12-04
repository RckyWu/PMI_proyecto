"""
Servicio de manejo de eventos del hardware
Procesa y clasifica eventos recibidos del Raspberry Pi
"""


class EventService:
    """
    Servicio que procesa eventos del hardware y los clasifica.
    """
    
    def parse_event(self, raw_message):
        """
        Parsea un mensaje del hardware y lo convierte en un evento estructurado.
        
        Args:
            raw_message: str - Mensaje crudo del serial
        
        Returns:
            dict o None - Evento estructurado o None si no es un evento válido
            
        Estructura del evento:
        {
            'type': str,      # 'motion', 'smoke', 'panic', 'door', 'laser', 'lock', 'system'
            'device': str,    # Nombre del dispositivo
            'state': str,     # Estado específico del evento
            'message': str,   # Mensaje legible para el usuario
            'priority': str,  # 'low', 'medium', 'high', 'critical'
            'raw': str        # Mensaje original
        }
        """
        if not raw_message:
            return None
        
        # Ignorar mensajes de sistema
        if any(raw_message.startswith(prefix) for prefix in ["SYSTEM:", "SENSORES:", "HEARTBEAT:", "OK:", "ERROR_SERIAL"]):
            return None
        
        # Parsear formato "EVENT:TIPO:ESTADO"
        parts = raw_message.split(":")
        
        if len(parts) < 2 or parts[0] != "EVENT":
            return None
        
        event_type = parts[1]
        event_state = parts[2] if len(parts) > 2 else ""
        
        # Mapeo de tipos de hardware a tipos de evento
        event_map = {
            'PIR': {
                'type': 'motion',
                'device': 'Sensor PIR',
                'message': '🚶 Movimiento detectado',
                'priority': 'medium'
            },
            'HUMO': {
                'type': 'smoke',
                'device': 'Detector de Humo',
                'message': '💨 Humo detectado',
                'priority': 'high'
            },
            'PANICO': {
                'type': 'panic',
                'device': 'Botón de Pánico',
                'message': '🚨 ALARMA activada',
                'priority': 'critical'
            },
            'SILENCIO': {
                'type': 'panic',
                'device': 'Alarma Silenciosa',
                'message': '🚨 ALARMA SILENCIOSA activada',
                'priority': 'critical'
            },
            'PUERTA': {
                'type': 'door',
                'device': 'Sensor de Puerta',
                'message': f'🚪 Puerta/Ventana {event_state}',
                'priority': 'medium' if event_state == "ABIERTA" else 'low'
            },
            'LASER': {
                'type': 'laser',
                'device': 'Detector Láser',
                'message': f'🔴 Perímetro láser {event_state}',
                'priority': 'high' if event_state == "INTERRUMPIDO" else 'low'
            },
            'CERRADURA': {
                'type': 'lock',
                'device': 'Cerradura Inteligente',
                'message': f'🔒 Cerradura {event_state}',
                'priority': 'medium'
            }
        }
        
        if event_type not in event_map:
            return None
        
        event_info = event_map[event_type].copy()
        event_info['state'] = event_state
        event_info['raw'] = raw_message
        
        return event_info
    
    def should_notify(self, event):
        """
        Determina si un evento debe generar notificación.
        
        Args:
            event: dict - Evento estructurado
        
        Returns:
            bool - True si debe notificar
        """
        if not event:
            return False
        
        # Notificar eventos de prioridad media o superior
        return event.get('priority') in ['medium', 'high', 'critical']
    
    def should_show_alert(self, event):
        """
        Determina si un evento debe mostrar alerta visual en la UI.
        
        Args:
            event: dict - Evento estructurado
        
        Returns:
            bool - True si debe mostrar alerta
        """
        return event.get('priority') in ['high', 'critical'] if event else False