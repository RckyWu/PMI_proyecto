"""
Detector de Movimiento con Cámara - Integrado para VING
Adaptado para funcionar como dispositivo en device_detail_window.py
"""

import cv2
import numpy as np
from datetime import datetime
import threading
import queue
import time
import os
from pathlib import Path
from collections import deque


class DetectorMovimientoCamara:
    """
    Detector de movimiento con captura de fotogramas.
    Thread-safe para integración en dispositivos VING.
    """
    
    def __init__(self, carpeta_capturas="capturas_fotogramas", carpeta_historial="historial"):
        """Inicializa el detector"""
        # Configuración de carpetas
        self.carpeta_capturas = Path(carpeta_capturas)
        self.carpeta_historial = Path(carpeta_historial)
        self._crear_directorios()
        
        # Archivo de historial
        self.archivo_historial = self.carpeta_historial / "historial_movimientos.txt"
        self._inicializar_historial()
        
        # Configuración de cámara
        self.camara = None
        self.frame_actual = None
        self.frame_anterior = None
        
        # Buffer para estabilización
        self.buffer_frames = deque(maxlen=10)
        
        # Control de threading
        self.thread_captura = None
        self.ejecutando = False
        self.pausado = False
        self.lock = threading.Lock()
        self.evento_parada = threading.Event()
        
        # Cola de eventos
        self.cola_eventos = queue.Queue()
        
        # Estadísticas
        self.movimientos_detectados = 0
        self.capturas_guardadas = 0
        self.ultimo_tiempo_captura = 0
        self.cooldown_segundos = 5
        
        # Configuración de detección
        self._umbral_movimiento = 2500
        self._calidad_jpeg = 75
        self._redimensionar_a = (1280, 720)
        
        # Configuración de estabilización
        self.frames_estabilizacion = 5
        self.contador_estabilizacion = 0
        
        # Flag para captura manual
        self.captura_manual_solicitada = False
        
        # Callback para notificaciones
        self.callback_notificacion = None
        
    def _crear_directorios(self):
        """Crea las carpetas necesarias"""
        self.carpeta_capturas.mkdir(exist_ok=True)
        self.carpeta_historial.mkdir(exist_ok=True)
        
    def _inicializar_historial(self):
        """Inicializa el archivo de historial"""
        if not self.archivo_historial.exists():
            with open(self.archivo_historial, 'w', encoding='utf-8') as f:
                f.write("=== HISTORIAL DE MOVIMIENTOS ===\n")
                f.write(f"Creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def _registrar_en_historial(self, nombre_archivo, tipo="automatica"):
        """Registra captura en historial"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tipo_texto = "Captura manual" if tipo == "manual" else "Movimiento detectado"
        linea = f"{timestamp} - {tipo_texto} - {nombre_archivo}\n"
        
        with open(self.archivo_historial, 'a', encoding='utf-8') as f:
            f.write(linea)
    
    def set_callback_notificacion(self, callback):
        """Establece callback para notificaciones"""
        self.callback_notificacion = callback
    
    def iniciar_camara(self, indice=0):
        """Inicia la cámara"""
        if self.camara is not None:
            self.detener_camara()
            
        self.camara = cv2.VideoCapture(indice)
        if not self.camara.isOpened():
            raise Exception(f"No se pudo abrir cámara {indice}")
        
        # Configurar resolución
        self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        return True
    
    def detener_camara(self):
        """Detiene la cámara"""
        if self.camara is not None:
            self.camara.release()
            self.camara = None
    
    def iniciar_deteccion(self):
        """Inicia la detección de movimiento"""
        if self.ejecutando:
            return False
        
        if self.camara is None:
            raise Exception("Cámara no inicializada")
        
        self.ejecutando = True
        self.evento_parada.clear()
        
        self.thread_captura = threading.Thread(
            target=self._loop_deteccion,
            daemon=True
        )
        self.thread_captura.start()
        
        return True
    
    def detener_deteccion(self):
        """Detiene la detección"""
        if not self.ejecutando:
            return
        
        self.ejecutando = False
        self.evento_parada.set()
        
        if self.thread_captura:
            self.thread_captura.join(timeout=2)
    
    def pausar_deteccion(self):
        """Pausa la detección"""
        self.pausado = True
    
    def reanudar_deteccion(self):
        """Reanuda la detección"""
        self.pausado = False
    
    def _loop_deteccion(self):
        """Loop principal de detección"""
        while self.ejecutando and not self.evento_parada.is_set():
            try:
                if self.pausado:
                    time.sleep(0.1)
                    continue
                
                # Leer frame
                ret, frame = self.camara.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                with self.lock:
                    self.frame_actual = frame.copy()
                
                # Añadir al buffer
                self.buffer_frames.append(frame.copy())
                
                # Detectar movimiento
                if self._detectar_movimiento(frame):
                    self.movimientos_detectados += 1
                    self.contador_estabilizacion += 1
                    
                    if self.contador_estabilizacion >= self.frames_estabilizacion:
                        if self._puede_capturar():
                            self._capturar_y_guardar(frame, "automatica")
                            self.contador_estabilizacion = 0
                else:
                    self.contador_estabilizacion = 0
                
                # Captura manual
                if self.captura_manual_solicitada:
                    self._capturar_y_guardar(frame, "manual")
                    self.captura_manual_solicitada = False
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                print(f"Error en loop: {e}")
                time.sleep(0.1)
    
    def _detectar_movimiento(self, frame):
        """Detecta movimiento en el frame"""
        # Convertir a escala de grises
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Primer frame
        if self.frame_anterior is None:
            self.frame_anterior = gray
            return False
        
        # Diferencia entre frames
        frame_diff = cv2.absdiff(self.frame_anterior, gray)
        thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Calcular área de cambio
        area_cambio = np.sum(thresh) / 255
        
        # Actualizar frame anterior
        self.frame_anterior = gray
        
        # Retornar si hay movimiento
        return area_cambio > self._umbral_movimiento
    
    def _puede_capturar(self):
        """Verifica si puede capturar (cooldown)"""
        tiempo_actual = time.time()
        if tiempo_actual - self.ultimo_tiempo_captura < self.cooldown_segundos:
            return False
        return True
    
    def _capturar_y_guardar(self, frame, tipo="automatica"):
        """Captura y guarda el frame"""
        try:
            # Actualizar tiempo
            self.ultimo_tiempo_captura = time.time()
            
            # Nombre del archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tipo_prefijo = "manual" if tipo == "manual" else "auto"
            nombre_archivo = f"captura_{tipo_prefijo}_{timestamp}.jpg"
            ruta_completa = self.carpeta_capturas / nombre_archivo
            
            # Redimensionar
            frame_guardado = cv2.resize(frame, self._redimensionar_a)
            
            # Guardar
            cv2.imwrite(str(ruta_completa), frame_guardado, 
                       [cv2.IMWRITE_JPEG_QUALITY, self._calidad_jpeg])
            
            # Registrar
            self.capturas_guardadas += 1
            self._registrar_en_historial(nombre_archivo, tipo)
            
            # Notificar
            evento = {
                'tipo': 'captura_guardada',
                'archivo': nombre_archivo,
                'ruta': str(ruta_completa),
                'tipo_captura': tipo,
                'timestamp': datetime.now()
            }
            
            self.cola_eventos.put(evento)
            
            # Callback
            if self.callback_notificacion:
                self.callback_notificacion(evento)
            
            return True
            
        except Exception as e:
            print(f"Error guardando captura: {e}")
            return False
    
    def solicitar_captura_manual(self):
        """Solicita una captura manual"""
        self.captura_manual_solicitada = True
    
    def obtener_frame_actual(self):
        """Obtiene el frame actual (thread-safe)"""
        with self.lock:
            if self.frame_actual is not None:
                return self.frame_actual.copy()
        return None
    
    def obtener_evento(self):
        """Obtiene evento de la cola (no bloqueante)"""
        try:
            return self.cola_eventos.get_nowait()
        except queue.Empty:
            return None
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas actuales"""
        return {
            'movimientos_detectados': self.movimientos_detectados,
            'capturas_guardadas': self.capturas_guardadas,
            'ejecutando': self.ejecutando,
            'pausado': self.pausado,
            'cooldown': self.cooldown_segundos,
            'umbral': self._umbral_movimiento
        }
    
    def configurar_sensibilidad(self, umbral):
        """Configura la sensibilidad (solo si está detenido)"""
        if not self.ejecutando:
            self._umbral_movimiento = umbral
            return True
        return False
    
    def configurar_cooldown(self, segundos):
        """Configura el tiempo de cooldown"""
        self.cooldown_segundos = segundos
    
    def leer_historial(self, ultimas_lineas=50):
        """Lee el historial"""
        try:
            if not self.archivo_historial.exists():
                return []
            
            with open(self.archivo_historial, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
            
            # Retornar últimas N líneas
            return lineas[-ultimas_lineas:] if len(lineas) > ultimas_lineas else lineas
            
        except Exception as e:
            print(f"Error leyendo historial: {e}")
            return []
    
    def obtener_capturas_recientes(self, n=10):
        """Obtiene las N capturas más recientes"""
        try:
            archivos = sorted(
                self.carpeta_capturas.glob("*.jpg"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            return [str(f) for f in archivos[:n]]
        except Exception as e:
            print(f"Error obteniendo capturas: {e}")
            return []
    
    def __del__(self):
        """Destructor"""
        self.detener_deteccion()
        self.detener_camara()
