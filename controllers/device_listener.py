import serial
import threading
import queue
import time

class DeviceListener:
    """
    Lee líneas desde un puerto serial en un hilo separado y las coloca en una queue.Queue.
    """

    def __init__(self, puerto="COM5", baud=115200, q=None):
        self.puerto = puerto
        self.baud = baud
        self.queue = q if q is not None else queue.Queue()
        self.ser = None
        self.running = False
        self.thread = None

    def start(self):
        """Inicia lectura en hilo separado."""
        self.ser = serial.Serial(self.puerto, self.baud, timeout=1)
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Detiene lectura."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _read_loop(self):
        """Ciclo principal de lectura."""
        while self.running:
            try:
                if raw := self.ser.readline():
                    try:
                        texto = raw.decode(errors="ignore").strip()
                    except Exception:
                        texto = str(raw)
                    if texto:
                        self.queue.put(texto)
                else:
                    time.sleep(0.05)
            except Exception as e:
                self.queue.put(f"ERROR_SERIAL: {repr(e)}")
                time.sleep(1)
