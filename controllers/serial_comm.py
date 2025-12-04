"""
Módulo de comunicación serial bidireccional con Raspberry Pi Pico
Maneja envío de comandos y recepción de eventos
"""

import serial
import threading
import queue
import time


class SerialCommunicator:
    """
    Comunicación bidireccional con Raspberry Pi Pico vía UART.
    - Recibe eventos del hardware
    - Envía comandos de activación/desactivación
    """

    def __init__(self, puerto="COM5", baud=115200):
        self.puerto = puerto
        self.baud = baud
        self.queue = queue.Queue()
        self.ser = None
        self.running = False
        self.thread = None
        self.connected = False

    def start(self):
        """Inicia la conexión y el hilo de lectura."""
        try:
            self.ser = serial.Serial(self.puerto, self.baud, timeout=1)
            self.connected = True
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"✓ Conectado a {self.puerto} @ {self.baud} baud")
            return True
        except Exception as e:
            print(f"✗ Error al conectar: {e}")
            self.connected = False
            return False

    def stop(self):
        """Detiene la conexión serial."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connected = False
        print("✓ Conexión serial cerrada")

    def _read_loop(self):
        """Ciclo de lectura en hilo separado."""
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    raw = self.ser.readline()
                    try:
                        texto = raw.decode(errors="ignore").strip()
                        if texto:
                            self.queue.put(texto)
                    except Exception as e:
                        print(f"Error decodificando: {e}")
                else:
                    time.sleep(0.05)
            except Exception as e:
                self.queue.put(f"ERROR_SERIAL: {repr(e)}")
                print(f"Error en lectura serial: {e}")
                time.sleep(1)

    def send_command(self, comando):
        """
        Envía un comando al Pico.
        Formato: CMD:ACCION:DISPOSITIVO
        
        Ejemplos:
        - CMD:ACTIVAR:PIR
        - CMD:DESACTIVAR:HUMO
        - CMD:CERRADURA:ABRIR
        - CMD:CERRADURA:CERRAR
        """
        if not self.connected or not self.ser or not self.ser.is_open:
            print(f"✗ No conectado. Comando no enviado: {comando}")
            return False
        
        try:
            # Agregar salto de línea si no lo tiene
            if not comando.endswith('\n'):
                comando += '\n'
            
            self.ser.write(comando.encode())
            print(f"→ Enviado: {comando.strip()}")
            return True
        except Exception as e:
            print(f"✗ Error enviando comando: {e}")
            return False

    def activar_dispositivo(self, nombre):
        """
        Envía comando para activar un dispositivo.
        nombre: "pir", "humo", "puerta", "laser", "panico", "presencia"
        """
        return self.send_command(f"CMD:ACTIVAR:{nombre.upper()}")

    def desactivar_dispositivo(self, nombre):
        """
        Envía comando para desactivar un dispositivo.
        """
        return self.send_command(f"CMD:DESACTIVAR:{nombre.upper()}")

    def abrir_cerradura(self):
        """Envía comando para abrir la cerradura."""
        return self.send_command("CMD:CERRADURA:ABRIR")

    def cerrar_cerradura(self):
        """Envía comando para cerrar la cerradura."""
        return self.send_command("CMD:CERRADURA:CERRAR")

    def activar_simulador_presencia(self):
        """Activa el simulador de presencia."""
        return self.send_command("CMD:ACTIVAR:PRESENCIA")

    def desactivar_simulador_presencia(self):
        """Desactiva el simulador de presencia."""
        return self.send_command("CMD:DESACTIVAR:PRESENCIA")

    def get_event(self):
        """
        Obtiene un evento de la cola (no bloqueante).
        Retorna None si no hay eventos.
        """
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

    def is_connected(self):
        """Retorna True si está conectado."""
        return self.connected and self.ser and self.ser.is_open


# Singleton global para compartir entre toda la app
_serial_comm = None


def get_serial_communicator(puerto="COM5", baud=115200):
    """
    Obtiene la instancia única del comunicador serial.
    Si no existe, la crea.
    """
    global _serial_comm
    if _serial_comm is None:
        _serial_comm = SerialCommunicator(puerto, baud)
    return _serial_comm


def init_serial(puerto="COM5", baud=115200):
    """
    Inicializa la comunicación serial.
    Retorna True si se conectó correctamente.
    """
    comm = get_serial_communicator(puerto, baud)
    return comm.start()


def close_serial():
    """Cierra la conexión serial."""
    global _serial_comm
    if _serial_comm:
        _serial_comm.stop()
        _serial_comm = None
