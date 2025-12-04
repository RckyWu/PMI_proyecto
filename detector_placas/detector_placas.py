"""
Detector de Placas de Vehículos - Versión 1.0
Características:
- Reconocimiento de placas usando OpenCV y OCR
- Guarda captura, bitácora y archivo de placa
- Threading robusto
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
import pytesseract
import re


class DetectorPlacas:
    def __init__(self, carpeta_capturas="capturas_placas", 
                 carpeta_historial="historial_placas",
                 carpeta_placas="placas_detectadas"):
        """
        Inicializa el detector de placas.
        
        Args:
            carpeta_capturas: Carpeta donde se guardarán las imágenes
            carpeta_historial: Carpeta donde se guardará el historial
            carpeta_placas: Carpeta donde se guardarán los txt con placas
        """
        # Configuración de carpetas
        self.carpeta_capturas = Path(carpeta_capturas)
        self.carpeta_historial = Path(carpeta_historial)
        self.carpeta_placas = Path(carpeta_placas)
        self._crear_directorios()
        
        # Archivos de salida
        self.archivo_historial = self.carpeta_historial / "historial_placas.txt"
        self.archivo_placas_total = self.carpeta_placas / "todas_las_placas.txt"
        self._inicializar_archivos()
        
        # Configuración de cámara
        self.camara = None
        self.frame_actual = None
        
        # Control de threading
        self.thread_captura = None
        self.ejecutando = False
        self.pausado = False
        self.lock = threading.Lock()
        self.evento_parada = threading.Event()
        
        # Cola de eventos
        self.cola_eventos = queue.Queue()
        
        # Estadísticas
        self.placas_detectadas = 0
        self.capturas_guardadas = 0
        self.ultimo_tiempo_captura = 0
        self.cooldown_segundos = 10  # Más tiempo para placas
        
        # Configuración de detección
        self._min_area = 2000  # Área mínima para posible placa
        self._calidad_jpeg = 80
        self._redimensionar_a = (1280, 720)
        
        # Configuración OCR
        self.config_tesseract = '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        # Buffer para estabilización
        self.buffer_frames = deque(maxlen=15)
        self.frames_estabilizacion = 8
        self.contador_estabilizacion = 0
        
        # Para evitar duplicados
        self.ultima_placa_detectada = ""
        self.tiempo_ultima_placa = 0
        self.cooldown_duplicados = 30  # Segundos para evitar misma placa
        
    def _crear_directorios(self):
        """Crea las carpetas necesarias."""
        self.carpeta_capturas.mkdir(exist_ok=True)
        self.carpeta_historial.mkdir(exist_ok=True)
        self.carpeta_placas.mkdir(exist_ok=True)
        
    def _inicializar_archivos(self):
        """Inicializa archivos de historial y placas."""
        if not self.archivo_historial.exists():
            with open(self.archivo_historial, 'w', encoding='utf-8') as f:
                f.write("=== HISTORIAL DE PLACAS DETECTADAS ===\n")
                f.write(f"Creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if not self.archivo_placas_total.exists():
            with open(self.archivo_placas_total, 'w', encoding='utf-8') as f:
                f.write("=== REGISTRO DE TODAS LAS PLACAS ===\n")
                f.write(f"Creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("FORMATO: PLACA | FECHA | HORA | ARCHIVO\n")
                f.write("-" * 60 + "\n")
    
    def _limpiar_texto_placa(self, texto):
        """
        Limpia y valida el texto de una placa.
        
        Args:
            texto: Texto crudo del OCR
            
        Returns:
            str: Placa limpia o cadena vacía si no es válida
        """
        if not texto:
            return ""
        
        # Quitar espacios y convertir a mayúsculas
        texto = texto.strip().upper()
        
        # Quitar caracteres especiales (mantener letras y números)
        texto = re.sub(r'[^A-Z0-9]', '', texto)
        
        # Validar formato básico (mínimo 5 caracteres, máximo 8)
        if len(texto) < 5 or len(texto) > 8:
            return ""
        
        # Contar letras y números
        letras = sum(1 for c in texto if c.isalpha())
        numeros = sum(1 for c in texto if c.isdigit())
        
        # Debe tener al menos 2 letras y 2 números
        if letras < 2 or numeros < 2:
            return ""
        
        return texto
    
    def _detectar_posibles_placas(self, frame):
        """
        Detecta posibles regiones de placas en el frame.
        
        Args:
            frame: Frame de entrada
            
        Returns:
            list: Lista de regiones (x, y, w, h)
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Aplicar desenfoque
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detectar bordes
        edged = cv2.Canny(blurred, 50, 200)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Ordenar contornos por área (más grandes primero)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        posibles_placas = []
        
        for contour in contours:
            # Aproximar el contorno
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            # Si tiene 4 vértices, podría ser una placa
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                
                # Validar proporciones típicas de placas (ancho > alto)
                ratio = w / float(h)
                area = w * h
                
                if 2.0 < ratio < 6.0 and area > self._min_area:
                    posibles_placas.append((x, y, w, h))
        
        return posibles_placas
    
    def _procesar_region_placa(self, frame, region):
        """
        Procesa una región para extraer texto de placa.
        
        Args:
            frame: Frame original
            region: (x, y, w, h) de la región
            
        Returns:
            tuple: (placa_texto, region_procesada)
        """
        x, y, w, h = region
        
        # Extraer región de interés
        roi = frame[y:y+h, x:x+w]
        
        # Preprocesamiento para OCR
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Aumentar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray_roi)
        
        # Binarización
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Dilatación para unir caracteres rotos
        kernel = np.ones((2,2), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        # Aplicar OCR
        try:
            texto = pytesseract.image_to_string(dilated, config=self.config_tesseract)
            placa_limpia = self._limpiar_texto_placa(texto)
            
            if placa_limpia:
                # Dibujar rectángulo en el frame original
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, placa_limpia, (x, y-10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                return placa_limpia, roi
                
        except Exception as e:
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': f'Error en OCR: {str(e)}'
            })
        
        return None, None
    
    def _guardar_captura_completa(self, frame, placa, region_placa):
        """
        Guarda todos los archivos: imagen, historial y placa.
        
        Args:
            frame: Frame completo
            placa: Texto de la placa detectada
            region_placa: Región de la placa (para recorte)
        """
        timestamp = datetime.now()
        nombre_base = timestamp.strftime('%Y-%m-%d_%H-%M-%S')
        
        # 1. Guardar imagen completa
        nombre_imagen = f"placa_{nombre_base}.jpg"
        ruta_imagen = self.carpeta_capturas / nombre_imagen
        
        # Redimensionar y comprimir
        frame_resized = cv2.resize(frame, self._redimensionar_a)
        cv2.imwrite(str(ruta_imagen), frame_resized, 
                   [cv2.IMWRITE_JPEG_QUALITY, self._calidad_jpeg])
        
        # 2. Guardar en historial
        with open(self.archivo_historial, 'a', encoding='utf-8') as f:
            linea = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - Placa: {placa} - {nombre_imagen}\n"
            f.write(linea)
        
        # 3. Guardar en archivo de placas
        archivo_placa = self.carpeta_placas / f"placa_{placa}_{nombre_base}.txt"
        with open(archivo_placa, 'w', encoding='utf-8') as f:
            f.write(f"PLACA: {placa}\n")
            f.write(f"FECHA: {timestamp.strftime('%Y-%m-%d')}\n")
            f.write(f"HORA: {timestamp.strftime('%H:%M:%S')}\n")
            f.write(f"ARCHIVO_IMAGEN: {nombre_imagen}\n")
            f.write(f"REGION: {region_placa}\n")
            f.write("-" * 40 + "\n")
        
        # 4. Agregar al archivo total de placas
        with open(self.archivo_placas_total, 'a', encoding='utf-8') as f:
            f.write(f"{placa} | {timestamp.strftime('%Y-%m-%d')} | {timestamp.strftime('%H:%M:%S')} | {nombre_imagen}\n")
        
        # Actualizar estadísticas
        with self.lock:
            self.placas_detectadas += 1
            self.capturas_guardadas += 1
            self.ultimo_tiempo_captura = time.time()
            self.ultima_placa_detectada = placa
            self.tiempo_ultima_placa = time.time()
        
        # Enviar evento
        self.cola_eventos.put({
            'tipo': 'placa_detectada',
            'placa': placa,
            'archivo': nombre_imagen,
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ruta_placa': str(archivo_placa)
        })
    
    def _puede_procesar(self):
        """
        Verifica si puede procesar nueva placa (cooldown y duplicados).
        
        Returns:
            bool: True si puede procesar
        """
        tiempo_actual = time.time()
        
        # Cooldown básico
        if tiempo_actual - self.ultimo_tiempo_captura < self.cooldown_segundos:
            return False
        
        # Evitar duplicados recientes
        if (self.ultima_placa_detectada and 
            tiempo_actual - self.tiempo_ultima_placa < self.cooldown_duplicados):
            return False
        
        return True
    
    def _bucle_deteccion(self):
        """Bucle principal de detección en el thread."""
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
                
                # Actualizar frame actual
                with self.lock:
                    self.frame_actual = frame.copy()
                
                # Agregar al buffer
                self.buffer_frames.append(frame.copy())
                
                # Solo procesar si puede (cooldown)
                if self._puede_procesar():
                    # Detectar posibles placas
                    posibles_regiones = self._detectar_posibles_placas(frame)
                    
                    if posibles_regiones:
                        self.contador_estabilizacion += 1
                        
                        # Esperar estabilización
                        if self.contador_estabilizacion >= self.frames_estabilizacion:
                            # Procesar la mejor región (primera, más grande)
                            mejor_region = posibles_regiones[0]
                            placa, region_placa = self._procesar_region_placa(frame, mejor_region)
                            
                            if placa and region_placa is not None:
                                # Usar el mejor frame del buffer
                                mejor_frame = self._seleccionar_mejor_frame()
                                if mejor_frame is not None:
                                    self._guardar_captura_completa(mejor_frame, placa, mejor_region)
                                
                                self.contador_estabilizacion = 0
                    else:
                        # Reiniciar contador si no detecta placas
                        if self.contador_estabilizacion > 0:
                            self.contador_estabilizacion = max(0, self.contador_estabilizacion - 1)
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                if not self.evento_parada.is_set():
                    self.cola_eventos.put({
                        'tipo': 'error',
                        'mensaje': f'Error en bucle de detección: {str(e)}'
                    })
                time.sleep(0.1)
    
    def _seleccionar_mejor_frame(self):
        """Selecciona el mejor frame del buffer."""
        if not self.buffer_frames:
            return None
        
        # Por ahora, devolver el más reciente
        return self.buffer_frames[-1].copy()
    
    def iniciar(self, indice_camara=0):
        """
        Inicia la cámara y el thread de detección.
        
        Args:
            indice_camara: Índice de la cámara
            
        Returns:
            bool: True si se inició correctamente
        """
        if self.ejecutando:
            return False
        
        try:
            self.evento_parada.clear()
            self.camara = cv2.VideoCapture(indice_camara)
            
            if not self.camara.isOpened():
                raise Exception("No se pudo abrir la cámara")
            
            # Configurar resolución
            self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Resetear variables
            self.buffer_frames.clear()
            self.contador_estabilizacion = 0
            
            # Iniciar thread
            self.ejecutando = True
            self.thread_captura = threading.Thread(target=self._bucle_deteccion, daemon=True)
            self.thread_captura.start()
            
            self.cola_eventos.put({
                'tipo': 'info',
                'mensaje': 'Detector de placas iniciado'
            })
            
            return True
            
        except Exception as e:
            self.ejecutando = False
            if self.camara is not None:
                self.camara.release()
                self.camara = None
            
            self.cola_eventos.put({
                'tipo': 'error',
                'mensaje': f'Error al iniciar: {str(e)}'
            })
            return False
    
    def detener(self):
        """Detiene la cámara y el thread."""
        if not self.ejecutando:
            return
        
        self.ejecutando = False
        self.evento_parada.set()
        
        if self.thread_captura is not None and self.thread_captura.is_alive():
            self.thread_captura.join(timeout=3)
        
        if self.camara is not None:
            try:
                self.camara.release()
            except:
                pass
            self.camara = None
        
        self.frame_actual = None
        self.pausado = False
        
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Detector detenido'
        })
    
    def pausar(self):
        """Pausa la detección."""
        if not self.ejecutando:
            return
        
        self.pausado = True
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Detección pausada'
        })
    
    def reanudar(self):
        """Reanuda la detección."""
        if not self.ejecutando:
            return
        
        self.pausado = False
        self.cola_eventos.put({
            'tipo': 'info',
            'mensaje': 'Detección reanudada'
        })
    
    def obtener_frame_actual(self):
        """Obtiene el frame actual."""
        with self.lock:
            if self.frame_actual is not None:
                return self.frame_actual.copy()
        return None
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas."""
        with self.lock:
            return {
                'placas_detectadas': self.placas_detectadas,
                'capturas_guardadas': self.capturas_guardadas,
                'estado': 'ejecutando' if self.ejecutando else 'detenido',
                'pausado': self.pausado,
                'cooldown_activo': not self._puede_procesar(),
                'ultima_placa': self.ultima_placa_detectada,
                'tiempo_restante_cooldown': max(0, self.cooldown_segundos - (time.time() - self.ultimo_tiempo_captura))
            }
    
    def obtener_evento(self, timeout=None):
        """Obtiene un evento de la cola."""
        try:
            return self.cola_eventos.get(block=timeout is not None, timeout=timeout)
        except queue.Empty:
            return None
    
    def configurar_parametros(self, min_area=None, calidad=None, cooldown=None):
        """
        Configura parámetros del detector.
        
        Args:
            min_area: Área mínima para detección
            calidad: Calidad JPEG
            cooldown: Cooldown entre detecciones
        """
        if self.ejecutando:
            return False
        
        if min_area:
            self._min_area = min_area
        if calidad:
            self._calidad_jpeg = calidad
        if cooldown:
            self.cooldown_segundos = cooldown
        
        return True


# Ejemplo de uso
if __name__ == "__main__":
    print("Instalación necesaria:")
    print("1. pip install pytesseract")
    print("2. pip install opencv-python pillow numpy")
    print("3. Instalar Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
    
    detector = DetectorPlacas()
    
    if detector.iniciar():
        print("\nDetector iniciado. Presiona Ctrl+C para detener.")
        try:
            while True:
                time.sleep(2)
                stats = detector.obtener_estadisticas()
                print(f"\nPlacas detectadas: {stats['placas_detectadas']}")
                print(f"Última placa: {stats['ultima_placa']}")
                
                evento = detector.obtener_evento()
                while evento:
                    print(f"Evento: {evento['tipo']}")
                    if evento['tipo'] == 'placa_detectada':
                        print(f"  Placa: {evento['placa']}")
                    evento = detector.obtener_evento()
                    
        except KeyboardInterrupt:
            print("\nDeteniendo...")
            detector.detener()
    else:
        print("Error al iniciar detector.")