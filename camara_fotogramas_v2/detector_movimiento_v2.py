"""
Detector de Movimiento con Cámara - Versión Mejorada
Características:
- Threading robusto con manejo de reinicio
- Captura manual independiente
- Configuración bloqueada durante ejecución
- Thread-safe para integración en aplicaciones
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


class DetectorMovimiento:
    def __init__(self, carpeta_capturas="capturas_fotogramas", carpeta_historial="historial"):
        """
        Inicializa el detector de movimiento.
        
        Args:
            carpeta_capturas: Carpeta donde se guardarán las imágenes
            carpeta_historial: Carpeta donde se guardará el historial
        """
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
        
        # Buffer para estabilización (almacena últimos N frames)
        self.buffer_frames = deque(maxlen=10)
        
        # Control de threading
        self.thread_captura = None
        self.ejecutando = False
        self.pausado = False
        self.lock = threading.Lock()
        self.evento_parada = threading.Event()
        
        # Cola de eventos para comunicación con la app principal
        self.cola_eventos = queue.Queue()
        
        # Estadísticas
        self.movimientos_detectados = 0
        self.capturas_guardadas = 0
        self.ultimo_tiempo_captura = 0
        self.cooldown_segundos = 5
        
        # Configuración de detección (INMUTABLE durante ejecución)
        self._umbral_movimiento = 2500  # Ajustar según sensibilidad deseada
        self._calidad_jpeg = 75  # 0-100, menor = más compresión
        self._redimensionar_a = (1280, 720)  # Resolución para guardar
        
        # Configuración de estabilización
        self.frames_estabilizacion = 5  # Frames a esperar antes de capturar
        self.contador_estabilizacion = 0
        
        # Flag para captura manual
        self.captura_manual_solicitada = False
        
    def _crear_directorios(self):
        """Crea las carpetas necesarias si no existen."""
        self.carpeta_capturas.mkdir(exist_ok=True)
        self.carpeta_historial.mkdir(exist_ok=True)
        
    def _inicializar_historial(self):
        """Inicializa el archivo de historial si no existe."""
        if not self.archivo_historial.exists():
            with open(self.archivo_historial, 'w', encoding='utf-8') as f:
                f.write("=== HISTORIAL DE MOVIMIENTOS ===\n")
                f.write(f"Creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def _registrar_en_historial(self, nombre_archivo, tipo="automatica"):
        """
        Registra la captura en el historial.
        
        Args:
            nombre_archivo: Nombre del archivo guardado
            tipo: Tipo de captura (automatica/manual)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tipo_texto = "Captura manual" if tipo == "manual" else "Movimiento detectado"
        linea = f"{timestamp} - {tipo_texto} - {nombre_archivo}\n"
        
        with open(self.archivo_historial, 'a', encoding='utf-8') as f:
            f.write(linea)
    
    def _calcular_nitidez(self, frame):
        """
        Calcula la nitidez de un frame usando la varianza del Laplaciano.
        
        Args:
            frame: Frame a evaluar
            
        Returns:
            float: Valor de nitidez
        """
        if frame is None:
            return 0
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return laplacian.var()
    
    def _seleccionar_frame_mas_nitido(self):
        """
        Selecciona el frame más nítido del buffer.
        
        Returns:
            numpy.ndarray: Frame más nítido
        """
        if not self.buffer_frames:
            return None
        
        mejor_frame = None
        mejor_nitidez = 0
        
        for frame in self.buffer_frames:
            nitidez = self._calcular_nitidez(frame)
            if nitidez > mejor_nitidez:
                mejor_nitidez = nitidez
                mejor_frame = frame.copy()
        
        return mejor_frame
    
    def _comprimir_y_guardar_imagen(self, frame, nombre_archivo):
        """
        Comprime y guarda la imagen optimizada.
        
        Args:
            frame: Frame a guardar
            nombre_archivo: Nombre del archivo (sin ruta)
            
        Returns:
            tuple: (exito: bool, tamaño_kb: float)
        """
        try:
            # Redimensionar para reducir tamaño
            frame_redimensionado = cv2.resize(frame, self._redimensionar_a)
            
            # Configurar parámetros de compresión JPEG
            parametros_jpeg = [
                cv2.IMWRITE_JPEG_QUALITY, self._calidad_jpeg,
                cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                cv2.IMWRITE_JPEG_PROGRESSIVE, 1
            ]
            
            # Guardar imagen
            ruta_completa = self.carpeta_capturas / nombre_archivo
            exito = cv2.imwrite(str(ruta_completa), frame_redimensionado, parametros_jpeg)
            
            if exito:
                tamaño_kb = os.path.getsize(ruta_completa) / 1024
                return True, tamaño_kb
            
            return False, 0
            
        except Exception as e:
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': f'Error al guardar imagen: {str(e)}'
            })
            return False, 0
    
    def _detectar_movimiento(self, frame):
        """
        Detecta movimiento comparando frames.
        
        Args:
            frame: Frame actual
            
        Returns:
            bool: True si se detectó movimiento
        """
        if self.frame_anterior is None:
            self.frame_anterior = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.frame_anterior = cv2.GaussianBlur(self.frame_anterior, (21, 21), 0)
            return False
        
        # Convertir a escala de grises y aplicar desenfoque
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Calcular diferencia absoluta
        diferencia = cv2.absdiff(self.frame_anterior, gray)
        umbral = cv2.threshold(diferencia, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilatar el umbral para rellenar agujeros
        umbral = cv2.dilate(umbral, None, iterations=2)
        
        # Encontrar contornos
        contornos, _ = cv2.findContours(umbral.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Actualizar frame anterior
        self.frame_anterior = gray
        
        # Verificar si hay movimiento significativo
        for contorno in contornos:
            if cv2.contourArea(contorno) > self._umbral_movimiento:
                return True
        
        return False
    
    def _puede_capturar(self):
        """
        Verifica si ha pasado suficiente tiempo desde la última captura (cooldown).
        
        Returns:
            bool: True si puede capturar
        """
        tiempo_actual = time.time()
        if tiempo_actual - self.ultimo_tiempo_captura >= self.cooldown_segundos:
            return True
        return False
    
    def _procesar_captura(self, tipo="automatica"):
        """
        Procesa la captura: selecciona el mejor frame, lo guarda y registra.
        
        Args:
            tipo: Tipo de captura ("automatica" o "manual")
        """
        # Seleccionar el frame más nítido del buffer
        mejor_frame = self._seleccionar_frame_mas_nitido()
        
        if mejor_frame is None:
            return
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        prefijo = "manual_" if tipo == "manual" else ""
        nombre_archivo = f"{prefijo}{timestamp}.jpg"
        
        # Guardar imagen
        exito, tamaño_kb = self._comprimir_y_guardar_imagen(mejor_frame, nombre_archivo)
        
        if exito:
            # Registrar en historial
            self._registrar_en_historial(nombre_archivo, tipo)
            
            # Actualizar estadísticas
            with self.lock:
                self.capturas_guardadas += 1
            
            # Enviar evento a la cola
            self.cola_eventos.put({
                'tipo': 'captura',
                'archivo': nombre_archivo,
                'timestamp': timestamp,
                'tamaño_kb': round(tamaño_kb, 2),
                'tipo_captura': tipo
            })
            
            # Actualizar tiempo de última captura solo si es automática
            if tipo == "automatica":
                self.ultimo_tiempo_captura = time.time()
            
            # Reiniciar contador de estabilización
            self.contador_estabilizacion = 0
    
    def _bucle_captura(self):
        """Bucle principal de captura en el thread."""
        while not self.evento_parada.is_set():
            if self.pausado:
                time.sleep(0.1)
                continue
            
            try:
                ret, frame = self.camara.read()
                
                if not ret:
                    self.cola_eventos.put({
                        'tipo': 'error',
                        'mensaje': 'Error al leer frame de la cámara'
                    })
                    time.sleep(0.1)
                    continue
                
                # Actualizar frame actual (thread-safe)
                with self.lock:
                    self.frame_actual = frame.copy()
                
                # Agregar frame al buffer
                self.buffer_frames.append(frame.copy())
                
                # Verificar si hay captura manual solicitada
                if self.captura_manual_solicitada:
                    self.captura_manual_solicitada = False
                    self._procesar_captura(tipo="manual")
                
                # Detectar movimiento automático
                if self._detectar_movimiento(frame):
                    with self.lock:
                        self.movimientos_detectados += 1
                    
                    # Incrementar contador de estabilización
                    self.contador_estabilizacion += 1
                    
                    # Si ya pasó el período de estabilización y puede capturar
                    if self.contador_estabilizacion >= self.frames_estabilizacion and self._puede_capturar():
                        self._procesar_captura(tipo="automatica")
                else:
                    # Reiniciar contador si no hay movimiento
                    self.contador_estabilizacion = 0
                
                # Pequeña pausa para no saturar CPU
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                if not self.evento_parada.is_set():
                    self.cola_eventos.put({
                        'tipo': 'error',
                        'mensaje': f'Error en bucle de captura: {str(e)}'
                    })
                    time.sleep(0.1)
    
    def iniciar(self, indice_camara=0):
        """
        Inicia la cámara y el thread de detección.
        
        Args:
            indice_camara: Índice de la cámara (0 = cámara por defecto)
            
        Returns:
            bool: True si se inició correctamente
        """
        if self.ejecutando:
            return False
        
        try:
            # Resetear evento de parada
            self.evento_parada.clear()
            
            # Inicializar cámara
            self.camara = cv2.VideoCapture(indice_camara)
            
            if not self.camara.isOpened():
                raise Exception("No se pudo abrir la cámara")
            
            # Configurar resolución de captura
            self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Resetear variables
            self.frame_anterior = None
            self.buffer_frames.clear()
            
            # Iniciar thread
            self.ejecutando = True
            self.thread_captura = threading.Thread(target=self._bucle_captura, daemon=True)
            self.thread_captura.start()
            
            self.cola_eventos.put({
                'tipo': 'info',
                'mensaje': 'Detector iniciado correctamente'
            })
            
            return True
            
        except Exception as e:
            self.ejecutando = False
            if self.camara is not None:
                self.camara.release()
                self.camara = None
            
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': f'Error al iniciar cámara: {str(e)}'
            })
            return False
    
    def detener(self):
        """Detiene la cámara y el thread limpiamente."""
        if not self.ejecutando:
            return
        
        self.ejecutando = False
        self.evento_parada.set()
        
        # Esperar a que termine el thread
        if self.thread_captura is not None and self.thread_captura.is_alive():
            self.thread_captura.join(timeout=3)
        
        # Liberar cámara
        if self.camara is not None:
            try:
                self.camara.release()
            except:
                pass
            self.camara = None
        
        # Limpiar estado
        self.frame_actual = None
        self.frame_anterior = None
        self.pausado = False
        
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Detector detenido'
        })
    
    def pausar(self):
        """Pausa la detección de movimiento."""
        if not self.ejecutando:
            return
        
        self.pausado = True
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Detección pausada'
        })
    
    def reanudar(self):
        """Reanuda la detección de movimiento."""
        if not self.ejecutando:
            return
        
        self.pausado = False
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Detección reanudada'
        })
    
    def capturar_manual(self):
        """
        Solicita una captura manual independiente de la detección de movimiento.
        La captura se procesará en el siguiente frame disponible.
        """
        if not self.ejecutando or self.pausado:
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': 'El detector debe estar activo para capturar manualmente'
            })
            return False
        
        self.captura_manual_solicitada = True
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Captura manual solicitada'
        })
        return True
    
    def obtener_frame_actual(self):
        """
        Obtiene el frame actual (thread-safe).
        
        Returns:
            numpy.ndarray: Frame actual o None
        """
        with self.lock:
            if self.frame_actual is not None:
                return self.frame_actual.copy()
        return None
    
    def obtener_estadisticas(self):
        """
        Obtiene estadísticas actuales (thread-safe).
        
        Returns:
            dict: Diccionario con estadísticas
        """
        with self.lock:
            return {
                'movimientos_detectados': self.movimientos_detectados,
                'capturas_guardadas': self.capturas_guardadas,
                'estado': 'ejecutando' if self.ejecutando else 'detenido',
                'pausado': self.pausado,
                'cooldown_activo': not self._puede_capturar(),
                'tiempo_restante_cooldown': max(0, self.cooldown_segundos - (time.time() - self.ultimo_tiempo_captura))
            }
    
    def obtener_evento(self, timeout=None):
        """
        Obtiene un evento de la cola.
        
        Args:
            timeout: Tiempo máximo de espera (None = no bloquear)
            
        Returns:
            dict: Evento o None si no hay eventos
        """
        try:
            return self.cola_eventos.get(block=timeout is not None, timeout=timeout)
        except queue.Empty:
            return None
    
    def configurar_sensibilidad(self, umbral_movimiento):
        """
        Configura la sensibilidad de detección.
        SOLO se puede cambiar cuando el detector está detenido.
        
        Args:
            umbral_movimiento: Área mínima de contorno para detectar movimiento
            
        Returns:
            bool: True si se configuró correctamente
        """
        if self.ejecutando:
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': 'No se puede cambiar la sensibilidad mientras el detector está activo'
            })
            return False
        
        self._umbral_movimiento = umbral_movimiento
        return True
    
    def configurar_compresion(self, calidad=75, resolucion=(1280, 720)):
        """
        Configura los parámetros de compresión de imágenes.
        SOLO se puede cambiar cuando el detector está detenido.
        
        Args:
            calidad: Calidad JPEG (0-100)
            resolucion: Tupla (ancho, alto) para redimensionar
            
        Returns:
            bool: True si se configuró correctamente
        """
        if self.ejecutando:
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': 'No se puede cambiar la compresión mientras el detector está activo'
            })
            return False
        
        self._calidad_jpeg = calidad
        self._redimensionar_a = resolucion
        return True
    
    def configurar_cooldown(self, segundos):
        """
        Configura el tiempo de cooldown entre capturas.
        
        Args:
            segundos: Segundos de cooldown
        """
        self.cooldown_segundos = segundos
    
    def obtener_configuracion(self):
        """
        Obtiene la configuración actual.
        
        Returns:
            dict: Configuración actual
        """
        return {
            'umbral_movimiento': self._umbral_movimiento,
            'calidad_jpeg': self._calidad_jpeg,
            'resolucion': self._redimensionar_a,
            'cooldown_segundos': self.cooldown_segundos
        }


# Ejemplo de uso básico
if __name__ == "__main__":
    detector = DetectorMovimiento()
    
    print("Iniciando detector de movimiento...")
    if detector.iniciar():
        print("Detector iniciado. Presiona Ctrl+C para detener.")
        
        try:
            while True:
                time.sleep(5)
                stats = detector.obtener_estadisticas()
                print(f"\nEstadísticas:")
                print(f"  Movimientos detectados: {stats['movimientos_detectados']}")
                print(f"  Capturas guardadas: {stats['capturas_guardadas']}")
                print(f"  Estado: {stats['estado']}")
                
                # Procesar eventos
                evento = detector.obtener_evento()
                while evento:
                    print(f"Evento: {evento}")
                    evento = detector.obtener_evento()
                    
        except KeyboardInterrupt:
            print("\nDeteniendo detector...")
            detector.detener()
            print("Detector detenido.")
    else:
        print("Error al iniciar el detector.")
