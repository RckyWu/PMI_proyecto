"""
Servicio de comunicación serial
Encapsula toda la lógica de envío de comandos al hardware
"""

from controllers.serial_comm import get_serial_communicator


class SerialService:
    """
    Servicio que maneja comandos hacia el Raspberry Pi Pico.
    Abstrae los detalles de comunicación serial.
    """
    
    def __init__(self):
        self.serial_comm = get_serial_communicator()
        
    def is_connected(self):
        """Verifica si hay conexión serial activa"""
        return self.serial_comm and self.serial_comm.is_connected()
    
    def activate_device(self, device_type):
        """
        Activa un dispositivo según su tipo.
        
        Args:
            device_type: str - Tipo de dispositivo (ej: "Sensor_de_Movimiento_Universal")
        
        Returns:
            bool - True si el comando se envió correctamente
        """
        if not self.is_connected():
            print("⚠️ No hay conexión serial")
            return False
        
        # Mapeo de tipos a comandos
        command_map = {
            "sensor_de_movimiento_universal": "pir",
            "detector_laser": "laser",
            "detector_láser": "laser",
            "boton_de_panico": "panico",
            "botón_de_pánico": "panico",
            "simulador_de_presencia": "presencia",
            "alarma_silenciosa": "panico",
            "detector_de_humo": "humo",
            "sensor_de_movimiento_para_entradas": "puerta",
        }
        
        # Normalizar tipo
        normalized = device_type.lower().replace(" ", "_")
        
        if command := command_map.get(normalized):
            return self.serial_comm.activar_dispositivo(command)
        
        print(f"⚠️ Tipo de dispositivo no reconocido: {device_type}")
        return False
    
    def deactivate_device(self, device_type):
        """
        Desactiva un dispositivo según su tipo.
        
        Args:
            device_type: str - Tipo de dispositivo
        
        Returns:
            bool - True si el comando se envió correctamente
        """
        if not self.is_connected():
            print("⚠️ No hay conexión serial")
            return False
        
        # Mapeo de tipos a comandos
        command_map = {
            "sensor_de_movimiento_universal": "pir",
            "detector_laser": "laser",
            "detector_láser": "laser",
            "boton_de_panico": "panico",
            "botón_de_pánico": "panico",
            "simulador_de_presencia": "presencia",
            "alarma_silenciosa": "panico",
            "detector_de_humo": "humo",
            "sensor_de_movimiento_para_entradas": "puerta",
        }
        
        normalized = device_type.lower().replace(" ", "_")
        
        if command := command_map.get(normalized):
            return self.serial_comm.desactivar_dispositivo(command)
        
        print(f"⚠️ Tipo de dispositivo no reconocido: {device_type}")
        return False
    
    def open_lock(self):
        """Abre la cerradura inteligente"""
        return False if not self.is_connected() else self.serial_comm.abrir_cerradura()
    
    def close_lock(self):
        """Cierra la cerradura inteligente"""
        return self.serial_comm.cerrar_cerradura() if self.is_connected() else False
    
    def get_event(self):
        """
        Obtiene el siguiente evento de la cola serial.
        
        Returns:
            str o None - Mensaje del hardware o None si no hay eventos
        """
        return None if not self.is_connected() else self.serial_comm.get_event()