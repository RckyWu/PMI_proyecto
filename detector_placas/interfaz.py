"""
Interfaz de Depuración para Detector de Placas
Muestra cada paso del procesamiento para ajustar parámetros
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import cv2
from PIL import Image, ImageTk
from detector_placas import DetectorPlacas
import time
import numpy as np


class VentanaDepuracionPlacas:
    def __init__(self, ventana_padre):
        self.ventana = tk.Toplevel(ventana_padre)
        self.ventana.title("🔍 DEPURACIÓN - Detector de Placas")
        self.ventana.geometry("1400x900")
        self.ventana.configure(bg='#1E1E1E')
        
        # Hacer modal
        self.ventana.transient(ventana_padre)
        self.ventana.grab_set()
        
        # Variables para procesamiento
        self.frame_original = None
        self.procesos = {}
        
        # Crear detector
        self.detector = DetectorPlacas()
        
        # Controles ajustables EN TIEMPO REAL
        self.parametros = {
            'min_area': tk.IntVar(value=2000),
            'threshold1': tk.IntVar(value=50),
            'threshold2': tk.IntVar(value=200),
            'blur_size': tk.IntVar(value=5),
            'contrast': tk.DoubleVar(value=2.0),
            'min_ratio': tk.DoubleVar(value=2.0),
            'max_ratio': tk.DoubleVar(value=6.0),
            'cooldown': tk.IntVar(value=10)
        }
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Iniciar actualizaciones
        self.actualizar_video()
        self.ventana.after(100, self.iniciar_camara)
        
        # Manejar cierre
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)
    
    def crear_interfaz(self):
        """Crea la interfaz completa de depuración."""
        # Frame principal con pestañas
        notebook = ttk.Notebook(self.ventana)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Pestaña 1: Visión en tiempo real
        tab_vision = tk.Frame(notebook, bg='#1E1E1E')
        notebook.add(tab_vision, text="👁️ Visión en Tiempo Real")
        self.crear_tab_vision(tab_vision)
        
        # Pestaña 2: Procesamiento paso a paso
        tab_proceso = tk.Frame(notebook, bg='#1E1E1E')
        notebook.add(tab_proceso, text="⚙️ Proceso Paso a Paso")
        self.crear_tab_proceso(tab_proceso)
        
        # Pestaña 3: Controles y Configuración
        tab_controles = tk.Frame(notebook, bg='#1E1E1E')
        notebook.add(tab_controles, text="🎛️ Controles")
        self.crear_tab_controles(tab_controles)
    
    def crear_tab_vision(self, parent):
        """Crea la pestaña de visión en tiempo real."""
        # Frame principal con dos columnas
        main_frame = tk.Frame(parent, bg='#1E1E1E')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Columna izquierda: Video original con detecciones
        left_frame = tk.Frame(main_frame, bg='#1E1E1E')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_frame, text="🎥 VIDEO ORIGINAL + DETECCIONES", 
                font=("Arial", 12, "bold"), bg='#1E1E1E', fg='white').pack(pady=(0, 10))
        
        self.canvas_original = tk.Canvas(left_frame, width=640, height=480, 
                                        bg='black', highlightthickness=2,
                                        highlightbackground='#3498DB')
        self.canvas_original.pack()
        
        # Overlay de información
        info_frame = tk.Frame(left_frame, bg='#2C3E50', relief=tk.RAISED, borderwidth=2)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.label_info = tk.Label(info_frame, text="Esperando detecciones...", 
                                  font=("Arial", 10), bg='#2C3E50', fg='white')
        self.label_info.pack(padx=10, pady=5)
        
        # Columna derecha: Procesamiento intermedio
        right_frame = tk.Frame(main_frame, bg='#1E1E1E')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Grid 2x2 para procesos
        procesos_frame = tk.Frame(right_frame, bg='#1E1E1E')
        procesos_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. Escala de grises
        frame_gris = tk.LabelFrame(procesos_frame, text="Escala de Grises", 
                                  bg='#2C3E50', fg='white', font=("Arial", 10))
        frame_gris.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.canvas_gris = tk.Canvas(frame_gris, width=300, height=200, bg='black')
        self.canvas_gris.pack()
        
        # 2. Bordes (Canny)
        frame_bordes = tk.LabelFrame(procesos_frame, text="Detección de Bordes", 
                                    bg='#2C3E50', fg='white', font=("Arial", 10))
        frame_bordes.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.canvas_bordes = tk.Canvas(frame_bordes, width=300, height=200, bg='black')
        self.canvas_bordes.pack()
        
        # 3. Contornos detectados
        frame_contornos = tk.LabelFrame(procesos_frame, text="Contornos Encontrados", 
                                       bg='#2C3E50', fg='white', font=("Arial", 10))
        frame_contornos.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        self.canvas_contornos = tk.Canvas(frame_contornos, width=300, height=200, bg='black')
        self.canvas_contornos.pack()
        
        # 4. Posibles placas
        frame_placas = tk.LabelFrame(procesos_frame, text="Posibles Placas", 
                                    bg='#2C3E50', fg='white', font=("Arial", 10))
        frame_placas.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        self.canvas_placas = tk.Canvas(frame_placas, width=300, height=200, bg='black')
        self.canvas_placas.pack()
        
        # Configurar grid
        procesos_frame.grid_columnconfigure(0, weight=1)
        procesos_frame.grid_columnconfigure(1, weight=1)
        procesos_frame.grid_rowconfigure(0, weight=1)
        procesos_frame.grid_rowconfigure(1, weight=1)
    
    def crear_tab_proceso(self, parent):
        """Crea la pestaña de proceso paso a paso."""
        # Frame con scroll
        canvas = tk.Canvas(parent, bg='#1E1E1E', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1E1E1E')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Procesamiento paso a paso
        self.crear_pasos_procesamiento(scrollable_frame)
    
    def crear_pasos_procesamiento(self, parent):
        """Crea la visualización de cada paso del procesamiento."""
        # Paso 1: Frame original
        paso1 = tk.LabelFrame(parent, text="1. Frame Original", 
                             font=("Arial", 11, "bold"), bg='#2C3E50', fg='white')
        paso1.pack(fill=tk.X, padx=10, pady=5)
        
        self.label_paso1 = tk.Label(paso1, text="Cargando...", 
                                   bg='#2C3E50', fg='#BDC3C7')
        self.label_paso1.pack(padx=10, pady=10)
        
        # Paso 2: Preprocesamiento
        paso2 = tk.LabelFrame(parent, text="2. Preprocesamiento", 
                             font=("Arial", 11, "bold"), bg='#2C3E50', fg='white')
        paso2.pack(fill=tk.X, padx=10, pady=5)
        
        subframe2 = tk.Frame(paso2, bg='#2C3E50')
        subframe2.pack(padx=10, pady=10)
        
        # Grises
        frame_gris_paso = tk.Frame(subframe2, bg='#34495E')
        frame_gris_paso.pack(side=tk.LEFT, padx=5)
        tk.Label(frame_gris_paso, text="Grises", bg='#34495E', fg='white').pack()
        self.canvas_paso_gris = tk.Canvas(frame_gris_paso, width=200, height=150, bg='black')
        self.canvas_paso_gris.pack()
        
        # Desenfoque
        frame_blur_paso = tk.Frame(subframe2, bg='#34495E')
        frame_blur_paso.pack(side=tk.LEFT, padx=5)
        tk.Label(frame_blur_paso, text="Desenfoque", bg='#34495E', fg='white').pack()
        self.canvas_paso_blur = tk.Canvas(frame_blur_paso, width=200, height=150, bg='black')
        self.canvas_paso_blur.pack()
        
        # Paso 3: Detección de bordes
        paso3 = tk.LabelFrame(parent, text="3. Detección de Bordes (Canny)", 
                             font=("Arial", 11, "bold"), bg='#2C3E50', fg='white')
        paso3.pack(fill=tk.X, padx=10, pady=5)
        
        self.canvas_paso_canny = tk.Canvas(paso3, width=400, height=200, bg='black')
        self.canvas_paso_canny.pack(padx=10, pady=10)
        
        # Paso 4: Contornos
        paso4 = tk.LabelFrame(parent, text="4. Encontrar Contornos", 
                             font=("Arial", 11, "bold"), bg='#2C3E50', fg='white')
        paso4.pack(fill=tk.X, padx=10, pady=5)
        
        subframe4 = tk.Frame(paso4, bg='#2C3E50')
        subframe4.pack(padx=10, pady=10)
        
        self.label_contornos = tk.Label(subframe4, text="Contornos encontrados: 0", 
                                       bg='#2C3E50', fg='white')
        self.label_contornos.pack()
        
        self.canvas_paso_contornos = tk.Canvas(subframe4, width=400, height=200, bg='black')
        self.canvas_paso_contornos.pack(pady=5)
        
        # Paso 5: Validación de placas
        paso5 = tk.LabelFrame(parent, text="5. Validación de Posibles Placas", 
                             font=("Arial", 11, "bold"), bg='#2C3E50', fg='white')
        paso5.pack(fill=tk.X, padx=10, pady=5)
        
        subframe5 = tk.Frame(paso5, bg='#2C3E50')
        subframe5.pack(padx=10, pady=10)
        
        self.label_validacion = tk.Label(subframe5, 
                                        text="Validando proporciones y área...", 
                                        bg='#2C3E50', fg='white')
        self.label_validacion.pack()
        
        self.canvas_paso_validacion = tk.Canvas(subframe5, width=400, height=200, bg='black')
        self.canvas_paso_validacion.pack(pady=5)
        
        # Paso 6: OCR y Resultado
        paso6 = tk.LabelFrame(parent, text="6. OCR y Resultado Final", 
                             font=("Arial", 11, "bold"), bg='#2C3E50', fg='white')
        paso6.pack(fill=tk.X, padx=10, pady=5)
        
        subframe6 = tk.Frame(paso6, bg='#2C3E50')
        subframe6.pack(padx=10, pady=10)
        
        self.label_placa = tk.Label(subframe6, text="PLACA: ---", 
                                   font=("Arial", 20, "bold"), 
                                   bg='#2C3E50', fg='#27AE60')
        self.label_placa.pack()
        
        self.label_confianza = tk.Label(subframe6, text="Confianza: --%", 
                                       bg='#2C3E50', fg='#BDC3C7')
        self.label_confianza.pack()
        
        self.canvas_paso_placa = tk.Canvas(subframe6, width=300, height=100, bg='black')
        self.canvas_paso_placa.pack(pady=10)
    
    def crear_tab_controles(self, parent):
        """Crea la pestaña de controles ajustables."""
        # Frame con scroll
        canvas = tk.Canvas(parent, bg='#1E1E1E', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1E1E1E')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Controles
        self.crear_controles_ajuste(scrollable_frame)
    
    def crear_controles_ajuste(self, parent):
        """Crea los controles deslizantes para ajustar parámetros."""
        # Título
        tk.Label(parent, text="🎛️ CONTROLES DE AJUSTE EN TIEMPO REAL", 
                font=("Arial", 14, "bold"), bg='#1E1E1E', fg='white').pack(pady=20)
        
        # 1. Área mínima
        self.crear_slider(parent, "Área Mínima para Placa:", 
                         self.parametros['min_area'], 500, 5000, 100)
        
        # 2. Umbrales Canny
        frame_canny = tk.LabelFrame(parent, text="Umbrales Canny", 
                                   bg='#2C3E50', fg='white', padx=10, pady=10)
        frame_canny.pack(fill=tk.X, padx=20, pady=10)
        
        self.crear_slider(frame_canny, "Umbral 1 (bajo):", 
                         self.parametros['threshold1'], 10, 100, 1, row=0)
        self.crear_slider(frame_canny, "Umbral 2 (alto):", 
                         self.parametros['threshold2'], 100, 300, 1, row=1)
        
        # 3. Desenfoque
        self.crear_slider(parent, "Tamaño de Desenfoque:", 
                         self.parametros['blur_size'], 1, 15, 2)
        
        # 4. Proporciones de placa
        frame_ratio = tk.LabelFrame(parent, text="Proporciones de Placa", 
                                   bg='#2C3E50', fg='white', padx=10, pady=10)
        frame_ratio.pack(fill=tk.X, padx=20, pady=10)
        
        self.crear_slider(frame_ratio, "Relación Mínima (ancho/alto):", 
                         self.parametros['min_ratio'], 1.0, 5.0, 0.1, 
                         tipo='double', row=0)
        self.crear_slider(frame_ratio, "Relación Máxima (ancho/alto):", 
                         self.parametros['max_ratio'], 3.0, 10.0, 0.1, 
                         tipo='double', row=1)
        
        # 5. Contraste
        self.crear_slider(parent, "Factor de Contraste:", 
                         self.parametros['contrast'], 1.0, 4.0, 0.1, tipo='double')
        
        # 6. Cooldown
        self.crear_slider(parent, "Cooldown entre detecciones (segundos):", 
                         self.parametros['cooldown'], 1, 30, 1)
        
        # Botones de acción
        frame_botones = tk.Frame(parent, bg='#1E1E1E')
        frame_botones.pack(pady=30)
        
        tk.Button(frame_botones, text="🔄 Aplicar Parámetros", 
                 command=self.aplicar_parametros,
                 bg='#3498DB', fg='white', font=("Arial", 11, "bold"),
                 padx=20, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(frame_botones, text="📸 Capturar Frame Actual", 
                 command=self.capturar_frame_para_analisis,
                 bg='#9B59B6', fg='white', font=("Arial", 11, "bold"),
                 padx=20, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(frame_botones, text="💾 Guardar Configuración", 
                 command=self.guardar_configuracion,
                 bg='#27AE60', fg='white', font=("Arial", 11, "bold"),
                 padx=20, pady=10).pack(side=tk.LEFT, padx=10)
    
    def crear_slider(self, parent, texto, variable, desde, hasta, paso, 
                    tipo='int', row=None):
        """Crea un control deslizante con label."""
        if row is not None:
            frame = tk.Frame(parent, bg=parent['bg'])
            frame.grid(row=row, column=0, sticky='ew', pady=5)
        else:
            frame = tk.Frame(parent, bg=parent['bg'])
            frame.pack(fill=tk.X, pady=10)
        
        tk.Label(frame, text=texto, bg=frame['bg'], fg='white', 
                font=("Arial", 10)).pack(anchor='w')
        
        if tipo == 'double':
            slider = tk.Scale(frame, from_=desde, to=hasta, resolution=paso,
                            orient=tk.HORIZONTAL, variable=variable,
                            bg='#34495E', fg='white', highlightthickness=0)
        else:
            slider = tk.Scale(frame, from_=desde, to=hasta,
                            orient=tk.HORIZONTAL, variable=variable,
                            bg='#34495E', fg='white', highlightthickness=0)
        
        slider.pack(fill=tk.X)
        
        # Label con valor actual
        value_label = tk.Label(frame, textvariable=variable, 
                              bg='#2C3E50', fg='#3498DB', font=("Arial", 9, "bold"))
        value_label.pack(anchor='e')
        
        return slider
    
    def iniciar_camara(self):
        """Inicia la cámara en modo prueba."""
        if not self.detector.iniciar():
            messagebox.showerror("Error", "No se pudo iniciar la cámara")
            self.ventana.destroy()
    
    def aplicar_parametros(self):
        """Aplica los parámetros ajustados."""
        # Aquí actualizarías los parámetros del detector
        self.detector.configurar_parametros(
            min_area=self.parametros['min_area'].get(),
            cooldown=self.parametros['cooldown'].get()
        )
        
        messagebox.showinfo("Parámetros", "Parámetros aplicados en tiempo real")
    
    def capturar_frame_para_analisis(self):
        """Captura el frame actual para análisis detallado."""
        if self.frame_original is not None:
            # Guardar frame para análisis
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"frame_debug_{timestamp}.jpg", self.frame_original)
            
            # Mostrar mensaje
            self.label_info.config(text=f"Frame guardado: frame_debug_{timestamp}.jpg")
            
            # Procesar este frame específico con más detalle
            self.procesar_frame_detallado(self.frame_original)
    
    def procesar_frame_detallado(self, frame):
        """Procesa un frame con todos los pasos visibles."""
        # 1. Guardar frame original
        self.mostrar_imagen_en_canvas(frame, self.canvas_paso_gris, "Original")
        
        # 2. Convertir a grises
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.mostrar_imagen_en_canvas(gray, self.canvas_paso_gris, "Grises", gray=True)
        
        # 3. Aplicar desenfoque
        blur_size = self.parametros['blur_size'].get()
        if blur_size % 2 == 0:  # Debe ser impar
            blur_size += 1
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        self.mostrar_imagen_en_canvas(blurred, self.canvas_paso_blur, "Desenfoque", gray=True)
        
        # 4. Detectar bordes (Canny)
        t1 = self.parametros['threshold1'].get()
        t2 = self.parametros['threshold2'].get()
        edges = cv2.Canny(blurred, t1, t2)
        self.mostrar_imagen_en_canvas(edges, self.canvas_paso_canny, "Bordes Canny", gray=True)
        
        # 5. Encontrar contornos
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        self.label_contornos.config(text=f"Contornos encontrados: {len(contours)}")
        
        # Dibujar contornos
        contour_img = frame.copy()
        cv2.drawContours(contour_img, contours, -1, (0, 255, 0), 2)
        self.mostrar_imagen_en_canvas(contour_img, self.canvas_paso_contornos, "Contornos")
        
        # 6. Filtrar posibles placas
        posibles_placas = []
        validation_img = frame.copy()
        
        min_area = self.parametros['min_area'].get()
        min_ratio = self.parametros['min_ratio'].get()
        max_ratio = self.parametros['max_ratio'].get()
        
        for contour in contours[:10]:  # Solo primeros 10 por velocidad
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            if len(approx) == 4:  # Cuadrilátero
                x, y, w, h = cv2.boundingRect(approx)
                ratio = w / float(h)
                area = w * h
                
                if area > min_area and min_ratio < ratio < max_ratio:
                    posibles_placas.append((x, y, w, h))
                    cv2.rectangle(validation_img, (x, y), (x+w, y+h), (0, 255, 255), 2)
        
        self.label_validacion.config(
            text=f"Posibles placas: {len(posibles_placas)} | "
                 f"Área min: {min_area} | Ratio: {min_ratio:.1f}-{max_ratio:.1f}"
        )
        self.mostrar_imagen_en_canvas(validation_img, self.canvas_paso_validacion, "Validación")
        
        # 7. Si hay posibles placas, intentar OCR
        if posibles_placas:
            # Tomar la primera placa
            x, y, w, h = posibles_placas[0]
            roi = frame[y:y+h, x:x+w]
            
            # Preprocesar para OCR
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Aumentar contraste
            contrast = self.parametros['contrast'].get()
            gray_roi = cv2.convertScaleAbs(gray_roi, alpha=contrast, beta=0)
            
            # Binarizar
            _, binary = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Mostrar ROI procesada
            self.mostrar_imagen_en_canvas(binary, self.canvas_paso_placa, "ROI para OCR", gray=True)
            
            # Intentar OCR (simplificado)
            try:
                import pytesseract
                texto = pytesseract.image_to_string(binary, 
                                                   config='--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                texto = texto.strip().upper()
                
                if len(texto) >= 5:
                    self.label_placa.config(text=f"PLACA: {texto}", fg='#27AE60')
                    self.label_confianza.config(text="Texto detectado (verificar formato)")
                else:
                    self.label_placa.config(text="PLACA: [texto muy corto]", fg='#E74C3C')
                    self.label_confianza.config(text=f"Texto: '{texto}' (no válido)")
                    
            except Exception as e:
                self.label_placa.config(text="ERROR OCR", fg='#E74C3C')
                self.label_confianza.config(text=str(e))
        else:
            self.label_placa.config(text="NO SE ENCONTRÓ PLACA", fg='#E74C3C')
            self.label_confianza.config(text="Ajuste parámetros o acerque la placa")
    
    def mostrar_imagen_en_canvas(self, imagen, canvas, titulo="", gray=False):
        """Muestra una imagen en un canvas de Tkinter."""
        if imagen is None:
            return
        
        # Convertir según el tipo
        if gray and len(imagen.shape) == 2:
            display_img = cv2.cvtColor(imagen, cv2.COLOR_GRAY2RGB)
        elif len(imagen.shape) == 3 and imagen.shape[2] == 3:  # BGR
            display_img = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
        else:
            display_img = imagen
        
        # Convertir a PIL
        h, w = display_img.shape[:2]
        scale = min(canvas.winfo_width()/w, canvas.winfo_height()/h) * 0.9
        new_w, new_h = int(w * scale), int(h * scale)
        
        if new_w > 0 and new_h > 0:
            img_resized = cv2.resize(display_img, (new_w, new_h))
            img_pil = Image.fromarray(img_resized)
            img_tk = ImageTk.PhotoImage(img_pil)
            
            canvas.delete("all")
            canvas.create_image(canvas.winfo_width()//2, canvas.winfo_height()//2, 
                              image=img_tk, anchor=tk.CENTER)
            canvas.image = img_tk  # Guardar referencia
            
            # Agregar título
            canvas.create_text(canvas.winfo_width()//2, 15, 
                             text=titulo, fill="white", 
                             font=("Arial", 10, "bold"))
    
    def actualizar_video(self):
        """Actualiza el video en tiempo real con procesamiento."""
        frame = self.detector.obtener_frame_actual()
        
        if frame is not None:
            self.frame_original = frame.copy()
            
            # 1. Mostrar frame original con posibles detecciones
            self.mostrar_imagen_en_canvas(frame, self.canvas_original, "Vista en Vivo")
            
            # 2. Procesar para mostrar pasos intermedios
            self.actualizar_procesos_intermedios(frame)
            
            # 3. Actualizar información
            stats = self.detector.obtener_estadisticas()
            info_text = (f"Placas detectadas: {stats['placas_detectadas']} | "
                        f"Última: {stats['ultima_placa'] or 'Ninguna'} | "
                        f"Estado: {'🟢 Activo' if stats['estado'] == 'ejecutando' else '🔴 Detenido'}")
            self.label_info.config(text=info_text)
        
        # Programar siguiente actualización
        if self.ventana.winfo_exists():
            self.ventana.after(33, self.actualizar_video)  # ~30 FPS
    
    def actualizar_procesos_intermedios(self, frame):
        """Actualiza las visualizaciones de los procesos intermedios."""
        # 1. Escala de grises
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.mostrar_imagen_en_canvas(gray, self.canvas_gris, "Grises", gray=True)
        
        # 2. Bordes Canny (con parámetros actuales)
        blur_size = self.parametros['blur_size'].get()
        if blur_size % 2 == 0:
            blur_size += 1
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        
        t1 = self.parametros['threshold1'].get()
        t2 = self.parametros['threshold2'].get()
        edges = cv2.Canny(blurred, t1, t2)
        self.mostrar_imagen_en_canvas(edges, self.canvas_bordes, "Bordes", gray=True)
        
        # 3. Contornos
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours_img = frame.copy()
        
        # Dibujar todos los contornos (primeros 20)
        for i, contour in enumerate(contours[:20]):
            color = (0, 255, 0) if i < 10 else (255, 0, 0)  # Verdes los primeros 10
            cv2.drawContours(contours_img, [contour], -1, color, 2)
        
        self.mostrar_imagen_en_canvas(contours_img, self.canvas_contornos, f"Contornos: {len(contours)}")
        
        # 4. Posibles placas
        posibles_img = frame.copy()
        min_area = self.parametros['min_area'].get()
        min_ratio = self.parametros['min_ratio'].get()
        max_ratio = self.parametros['max_ratio'].get()
        
        posibles = 0
        for contour in contours[:10]:  # Solo primeros 10
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                ratio = w / float(h)
                area = w * h
                
                if area > min_area and min_ratio < ratio < max_ratio:
                    posibles += 1
                    cv2.rectangle(posibles_img, (x, y), (x+w, y+h), (0, 255, 255), 3)
                    cv2.putText(posibles_img, f"R:{ratio:.1f}", (x, y-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        self.mostrar_imagen_en_canvas(posibles_img, self.canvas_placas, 
                                     f"Posibles: {posibles}")
    
    def guardar_configuracion(self):
        """Guarda la configuración actual a archivo."""
        config = {key: var.get() for key, var in self.parametros.items()}
        
        import json
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"config_placa_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=4)
        
        messagebox.showinfo("Guardado", f"Configuración guardada en {filename}")
    
    def cerrar(self):
        """Cierra la ventana limpiamente."""
        self.detector.detener()
        time.sleep(0.3)
        self.ventana.destroy()


# Interfaz principal simplificada
class InterfazPrincipalPlacas:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚗 Sistema de Reconocimiento de Placas")
        self.root.geometry("500x400")
        self.root.configure(bg='#2C3E50')
        
        # Título
        tk.Label(self.root, text="🚗 SISTEMA DE RECONOCIMIENTO DE PLACAS", 
                font=("Arial", 16, "bold"), bg='#2C3E50', fg='white').pack(pady=30)
        
        # Instrucciones
        tk.Label(self.root, text="Para detectar placas:", 
                font=("Arial", 12), bg='#2C3E50', fg='#BDC3C7').pack()
        
        instructions = [
            "1. Conecta una cámara web",
            "2. Abre la interfaz de depuración",
            "3. Ajusta parámetros en tiempo real",
            "4. Acerca una placa a la cámara",
            "5. ¡El sistema detectará automáticamente!"
        ]
        
        for i, text in enumerate(instructions, 1):
            tk.Label(self.root, text=text, font=("Arial", 10), 
                    bg='#2C3E50', fg='#ECF0F1').pack(pady=5)
        
        # Botón para abrir depuración
        btn_depurar = tk.Button(self.root, text="🔧 ABRIR INTERFAZ DE DEPURACIÓN", 
                               command=self.abrir_depuracion,
                               bg='#3498DB', fg='white', font=("Arial", 12, "bold"),
                               padx=30, pady=15, cursor='hand2')
        btn_depurar.pack(pady=40)
        
        # Botón para cerrar
        tk.Button(self.root, text="❌ Salir", command=self.root.quit,
                 bg='#E74C3C', fg='white', font=("Arial", 10)).pack()
        
        self.root.mainloop()
    
    def abrir_depuracion(self):
        """Abre la ventana de depuración."""
        VentanaDepuracionPlacas(self.root)


if __name__ == "__main__":
    print("🚗 Sistema de Reconocimiento de Placas - Modo Depuración")
    print("=" * 60)
    print("INSTRUCCIONES:")
    print("1. Abre la interfaz principal")
    print("2. Haz clic en 'Abrir Interfaz de Depuración'")
    print("3. Ajusta los parámetros en tiempo real")
    print("4. Usa una placa real o imagen en tu celular")
    print("5. Observa cada paso del procesamiento")
    print("=" * 60)
    
    InterfazPrincipalPlacas()