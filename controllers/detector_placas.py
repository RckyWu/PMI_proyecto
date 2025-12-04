"""
Detector de Placas de Costa Rica con OCR
Detecta movimiento, captura imagen, extrae placa con OCR y verifica contra lista autorizada
Formato de placas de Costa Rica: 6 dígitos (000000 a 999999)
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
import json
import re

# Intentar importar pytesseract para OCR
try:
    import pytesseract
    # Para Windows, descomentar y ajustar la ruta si es necesario:
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_DISPONIBLE = True
except ImportError:
    print("⚠️ pytesseract no disponible. Instalar con: pip install pytesseract")
    print("   También necesitas instalar Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
    OCR_DISPONIBLE = False


class DetectorPlacas:
    """Detector de placas con OCR para Costa Rica"""
    
    def __init__(self, carpeta_capturas="capturas_placas", archivo_placas="placas_autorizadas.json"):
        """
        Inicializa el detector de placas.
        
        Args:
            carpeta_capturas: Carpeta donde se guardarán las imágenes
            archivo_placas: Archivo JSON con placas autorizadas
        """
        # Configuración de carpetas
        self.carpeta_capturas = Path(carpeta_capturas)
        self.carpeta_capturas.mkdir(exist_ok=True)
        
        # Archivo de placas autorizadas
        self.archivo_placas = Path(archivo_placas)
        self.placas_autorizadas = self._cargar_placas()
        
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
        
        # Cola de eventos para notificaciones
        self.cola_eventos = queue.Queue()
        
        # Configuración de detección
        self.sensibilidad = 25  # Umbral para detección de movimiento
        self.min_area_movimiento = 5000  # Área mínima para considerar movimiento
        
        # Cooldown para evitar múltiples detecciones
        self.ultimo_analisis = 0
        self.cooldown_segundos = 5  # Segundos entre análisis
        
        # Callback para notificaciones
        self.callback_notificacion = None
        
        # Estado
        self.estado = "Detenido"
        
    def _cargar_placas(self):
        """Carga las placas autorizadas desde el archivo JSON"""
        if self.archivo_placas.exists():
            try:
                with open(self.archivo_placas, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('placas_autorizadas', []))
            except Exception as e:
                print(f"Error cargando placas: {e}")
                return set()
        else:
            # Crear archivo con placas de ejemplo
            placas_ejemplo = {
                'placas_autorizadas': [
                    '123456',
                    '789012',
                    '345678'
                ]
            }
            try:
                with open(self.archivo_placas, 'w', encoding='utf-8') as f:
                    json.dump(placas_ejemplo, f, indent=2)
                print(f"✅ Archivo de placas creado: {self.archivo_placas}")
                return set(placas_ejemplo['placas_autorizadas'])
            except Exception as e:
                print(f"Error creando archivo de placas: {e}")
                return set()
    
    def agregar_placa_autorizada(self, placa):
        """Agrega una placa a la lista de autorizadas"""
        placa = self._normalizar_placa(placa)
        if self._validar_formato_placa(placa):
            self.placas_autorizadas.add(placa)
            self._guardar_placas()
            return True
        return False
    
    def eliminar_placa_autorizada(self, placa):
        """Elimina una placa de la lista de autorizadas"""
        placa = self._normalizar_placa(placa)
        if placa in self.placas_autorizadas:
            self.placas_autorizadas.remove(placa)
            self._guardar_placas()
            return True
        return False
    
    def _guardar_placas(self):
        """Guarda las placas autorizadas en el archivo JSON"""
        try:
            data = {
                'placas_autorizadas': sorted(list(self.placas_autorizadas))
            }
            with open(self.archivo_placas, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando placas: {e}")
    
    def _normalizar_placa(self, placa):
        """Normaliza una placa: solo dígitos, 6 caracteres"""
        # Extraer solo dígitos
        digitos = ''.join(c for c in str(placa) if c.isdigit())
        # Rellenar con ceros a la izquierda si es necesario
        return digitos.zfill(6)[:6]
    
    def _validar_formato_placa(self, placa):
        """Valida que la placa tenga el formato correcto de Costa Rica"""
        # 6 dígitos del 0 al 9
        return bool(re.match(r'^\d{6}$', placa))
    
    def iniciar_camara(self, indice_camara=0):
        """Inicia la cámara"""
        if self.camara is not None:
            self.camara.release()
        
        self.camara = cv2.VideoCapture(indice_camara)
        if not self.camara.isOpened():
            raise Exception(f"No se pudo abrir la cámara {indice_camara}")
        
        # Configurar resolución (opcional)
        self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print(f"✅ Cámara iniciada: {indice_camara}")
    
    def detener_camara(self):
        """Detiene la cámara"""
        if self.camara is not None:
            self.camara.release()
            self.camara = None
            print("✅ Cámara detenida")
    
    def iniciar_deteccion(self):
        """Inicia el thread de detección de movimiento"""
        if self.ejecutando:
            print("⚠️ Detección ya está en ejecución")
            return
        
        if self.camara is None:
            raise Exception("La cámara no está inicializada")
        
        self.ejecutando = True
        self.pausado = False
        self.estado = "Detectando"
        
        self.thread_captura = threading.Thread(target=self._loop_deteccion, daemon=True)
        self.thread_captura.start()
        
        print("✅ Detección de placas iniciada")
    
    def detener_deteccion(self):
        """Detiene el thread de detección"""
        self.ejecutando = False
        self.estado = "Detenido"
        
        if self.thread_captura is not None:
            self.thread_captura.join(timeout=2.0)
        
        print("✅ Detección de placas detenida")
    
    def pausar(self):
        """Pausa la detección sin detener el thread"""
        self.pausado = True
        self.estado = "Pausado"
    
    def reanudar(self):
        """Reanuda la detección"""
        self.pausado = False
        self.estado = "Detectando"
    
    def _loop_deteccion(self):
        """Loop principal de detección (ejecuta en thread)"""
        print("🔄 Loop de detección iniciado")
        
        while self.ejecutando:
            if self.pausado:
                time.sleep(0.1)
                continue
            
            try:
                # Leer frame de la cámara
                ret, frame = self.camara.read()
                
                if not ret or frame is None:
                    print("⚠️ No se pudo leer el frame")
                    time.sleep(0.1)
                    continue
                
                # Guardar frame actual
                self.frame_actual = frame.copy()
                
                # Agregar al buffer
                self.buffer_frames.append(frame.copy())
                
                # Detectar movimiento
                if self._detectar_movimiento(frame):
                    # Verificar cooldown
                    tiempo_actual = time.time()
                    if tiempo_actual - self.ultimo_analisis >= self.cooldown_segundos:
                        print("🚗 Movimiento detectado - Analizando placa...")
                        self.ultimo_analisis = tiempo_actual
                        
                        # Analizar placa en thread separado para no bloquear
                        threading.Thread(
                            target=self._analizar_y_notificar,
                            args=(frame.copy(),),
                            daemon=True
                        ).start()
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                print(f"❌ Error en loop de detección: {e}")
                time.sleep(0.1)
        
        print("🛑 Loop de detección terminado")
    
    def _detectar_movimiento(self, frame):
        """Detecta si hay movimiento en el frame"""
        if self.frame_anterior is None:
            self.frame_anterior = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.frame_anterior = cv2.GaussianBlur(self.frame_anterior, (21, 21), 0)
            return False
        
        # Convertir a escala de grises y aplicar desenfoque
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Calcular diferencia absoluta
        diff = cv2.absdiff(self.frame_anterior, gray)
        
        # Aplicar umbral
        thresh = cv2.threshold(diff, self.sensibilidad, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Verificar si hay movimiento significativo
        movimiento_detectado = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area_movimiento:
                movimiento_detectado = True
                break
        
        # Actualizar frame anterior
        self.frame_anterior = gray
        
        return movimiento_detectado
    
    def _analizar_y_notificar(self, frame):
        """Analiza el frame, extrae placa y notifica si es necesario"""
        try:
            # Guardar captura
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_captura = self.carpeta_capturas / f"captura_{timestamp}.jpg"
            cv2.imwrite(str(ruta_captura), frame)
            
            # Extraer placa con OCR
            placa_detectada = self._extraer_placa_ocr(frame)
            
            if placa_detectada:
                print(f"📋 Placa detectada: {placa_detectada}")
                
                # Verificar si está autorizada
                if placa_detectada in self.placas_autorizadas:
                    print(f"✅ Placa autorizada: {placa_detectada}")
                    evento = {
                        'tipo': 'placa_autorizada',
                        'placa': placa_detectada,
                        'timestamp': datetime.now(),
                        'imagen': str(ruta_captura)
                    }
                else:
                    print(f"⚠️ PLACA NO AUTORIZADA: {placa_detectada}")
                    evento = {
                        'tipo': 'placa_no_autorizada',
                        'placa': placa_detectada,
                        'timestamp': datetime.now(),
                        'imagen': str(ruta_captura)
                    }
                    
                    # Notificar al callback si existe
                    if self.callback_notificacion:
                        try:
                            self.callback_notificacion(evento)
                        except Exception as e:
                            print(f"Error en callback: {e}")
                
                # Agregar a cola de eventos
                self.cola_eventos.put(evento)
            else:
                print("⚠️ No se pudo detectar placa en la imagen")
                
        except Exception as e:
            print(f"❌ Error analizando frame: {e}")
            import traceback
            traceback.print_exc()
    
    def _extraer_placa_ocr(self, frame):
        """Extrae el número de placa usando OCR"""
        if not OCR_DISPONIBLE:
            print("⚠️ OCR no disponible")
            return None
        
        try:
            # Preprocesar imagen para mejorar OCR
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Aplicar threshold adaptativo
            thresh = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            
            # Intentar detectar región de la placa (opcional - mejora precisión)
            placa_region = self._detectar_region_placa(gray)
            
            if placa_region is not None:
                # OCR solo en la región de la placa
                imagen_ocr = placa_region
            else:
                # OCR en toda la imagen
                imagen_ocr = thresh
            
            # Configurar OCR para solo números
            config_ocr = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
            
            # Extraer texto
            texto = pytesseract.image_to_string(imagen_ocr, config=config_ocr)
            
            # Limpiar y normalizar
            placa = self._normalizar_placa(texto)
            
            # Validar formato
            if self._validar_formato_placa(placa):
                return placa
            else:
                # Intentar con diferentes preprocesa mientos
                return self._ocr_alternativo(frame)
                
        except Exception as e:
            print(f"Error en OCR: {e}")
            return None
    
    def _ocr_alternativo(self, frame):
        """Intenta OCR con diferentes preprocessamientos"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Intentar con threshold simple
            _, thresh1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            config_ocr = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
            texto1 = pytesseract.image_to_string(thresh1, config=config_ocr)
            placa1 = self._normalizar_placa(texto1)
            if self._validar_formato_placa(placa1):
                return placa1
            
            # Intentar con inversión
            _, thresh2 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            texto2 = pytesseract.image_to_string(thresh2, config=config_ocr)
            placa2 = self._normalizar_placa(texto2)
            if self._validar_formato_placa(placa2):
                return placa2
            
            return None
            
        except Exception as e:
            print(f"Error en OCR alternativo: {e}")
            return None
    
    def _detectar_region_placa(self, gray):
        """
        Intenta detectar la región de la placa en la imagen.
        Retorna la región recortada o None si no se encuentra.
        """
        try:
            # Aplicar detección de bordes
            edges = cv2.Canny(gray, 50, 200)
            
            # Dilatar para conectar bordes
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(edges, kernel, iterations=1)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Buscar contornos rectangulares con aspect ratio de placa
            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
                # Aproximar contorno a polígono
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                # Verificar si es un rectángulo
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = w / float(h)
                    
                    # Placas típicamente tienen aspect ratio entre 2:1 y 5:1
                    if 2.0 <= aspect_ratio <= 5.0 and w > 100 and h > 20:
                        # Recortar región
                        placa_region = gray[y:y+h, x:x+w]
                        return placa_region
            
            return None
            
        except Exception as e:
            print(f"Error detectando región de placa: {e}")
            return None
    
    def obtener_frame_actual(self):
        """Obtiene el frame actual de la cámara"""
        return self.frame_actual.copy() if self.frame_actual is not None else None
    
    def obtener_placas_autorizadas(self):
        """Obtiene la lista de placas autorizadas"""
        return sorted(list(self.placas_autorizadas))
    
    def set_callback_notificacion(self, callback):
        """
        Establece el callback para notificaciones de placas no autorizadas.
        
        Args:
            callback: Función que recibe un diccionario con info del evento
        """
        self.callback_notificacion = callback
    
    def obtener_evento(self):
        """Obtiene el siguiente evento de la cola (no bloqueante)"""
        try:
            return self.cola_eventos.get_nowait()
        except queue.Empty:
            return None


# Función de prueba
def prueba_detector():
    """Función de prueba del detector"""
    print("=" * 60)
    print("DETECTOR DE PLACAS - PRUEBA")
    print("=" * 60)
    
    if not OCR_DISPONIBLE:
        print("\n❌ ERROR: pytesseract no está instalado")
        print("   Instalar con: pip install pytesseract")
        print("   También instalar Tesseract OCR:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        return
    
    detector = DetectorPlacas()
    
    # Mostrar placas autorizadas
    print(f"\n📋 Placas autorizadas: {detector.obtener_placas_autorizadas()}")
    
    # Callback para notificaciones
    def notificar(evento):
        print(f"\n🔔 NOTIFICACIÓN:")
        print(f"   Tipo: {evento['tipo']}")
        print(f"   Placa: {evento['placa']}")
        print(f"   Hora: {evento['timestamp']}")
        print(f"   Imagen: {evento['imagen']}")
    
    detector.set_callback_notificacion(notificar)
    
    try:
        # Iniciar cámara
        print("\n🎥 Iniciando cámara...")
        detector.iniciar_camara(0)
        
        # Iniciar detección
        print("🔍 Iniciando detección...")
        detector.iniciar_deteccion()
        
        print("\n✅ Sistema activo")
        print("   Presiona Ctrl+C para detener\n")
        
        # Mantener activo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        detector.detener_deteccion()
        detector.detener_camara()
        print("✅ Sistema detenido")


if __name__ == "__main__":
    prueba_detector()
