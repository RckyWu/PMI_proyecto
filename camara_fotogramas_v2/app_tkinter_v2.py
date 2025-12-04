"""
Aplicación Detector de Movimiento - Versión Mejorada
Características:
- Controles de configuración bloqueados durante ejecución
- Botón de captura manual
- Manejo robusto de inicio/parada
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import cv2
from PIL import Image, ImageTk
from detector_movimiento_v2 import DetectorMovimiento
import threading
import time


class AplicacionDetector:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("🎥 Detector de Movimiento v2.0")
        self.ventana.geometry("1200x750")
        self.ventana.configure(bg='#2C3E50')
        
        # Crear detector
        self.detector = DetectorMovimiento()
        
        # Variables de control
        self.actualizando = False
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Iniciar actualizaciones
        self.actualizar_video()
        self.actualizar_estadisticas()
        self.procesar_eventos()
        
        # Manejar cierre de ventana
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)
    
    def crear_interfaz(self):
        """Crea todos los elementos de la interfaz."""
        # Frame principal
        frame_principal = tk.Frame(self.ventana, bg='#2C3E50')
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ===== LADO IZQUIERDO: VIDEO =====
        frame_izquierdo = tk.Frame(frame_principal, bg='#2C3E50')
        frame_izquierdo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Título del video
        titulo_video = tk.Label(frame_izquierdo, text="📹 Video en Vivo", 
                               font=("Arial", 16, "bold"), bg='#2C3E50', fg='white')
        titulo_video.pack(pady=(0, 10))
        
        # Canvas para el video
        self.canvas_video = tk.Canvas(frame_izquierdo, width=800, height=600, 
                                      bg='black', highlightthickness=2, 
                                      highlightbackground='#3498DB')
        self.canvas_video.pack()
        
        # ===== LADO DERECHO: CONTROLES Y ESTADÍSTICAS =====
        frame_derecho = tk.Frame(frame_principal, bg='#2C3E50', width=350)
        frame_derecho.pack(side=tk.RIGHT, fill=tk.BOTH)
        frame_derecho.pack_propagate(False)
        
        # === SECCIÓN DE CONTROL ===
        frame_control = tk.LabelFrame(frame_derecho, text="⚙️ Control del Sistema", 
                                     font=("Arial", 12, "bold"), bg='#34495E', 
                                     fg='white', padx=15, pady=15)
        frame_control.pack(fill=tk.X, pady=(0, 10))
        
        # Botones de control en grid 2x2
        self.btn_iniciar = tk.Button(frame_control, text="▶️ Iniciar", 
                                     command=self.iniciar_detector,
                                     bg='#27AE60', fg='white', font=("Arial", 11, "bold"),
                                     padx=20, pady=10, cursor='hand2')
        self.btn_iniciar.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        self.btn_detener = tk.Button(frame_control, text="⏹️ Detener", 
                                     command=self.detener_detector,
                                     bg='#E74C3C', fg='white', font=("Arial", 11, "bold"),
                                     padx=20, pady=10, cursor='hand2', state='disabled')
        self.btn_detener.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.btn_pausar = tk.Button(frame_control, text="⏸️ Pausar", 
                                   command=self.pausar_detector,
                                   bg='#F39C12', fg='white', font=("Arial", 11, "bold"),
                                   padx=20, pady=10, cursor='hand2', state='disabled')
        self.btn_pausar.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        
        self.btn_reanudar = tk.Button(frame_control, text="▶️ Reanudar", 
                                     command=self.reanudar_detector,
                                     bg='#16A085', fg='white', font=("Arial", 11, "bold"),
                                     padx=20, pady=10, cursor='hand2', state='disabled')
        self.btn_reanudar.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        # Separador
        separador = ttk.Separator(frame_control, orient='horizontal')
        separador.grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        
        # Botón de captura manual (centrado, ocupa ambas columnas)
        self.btn_captura_manual = tk.Button(frame_control, text="📸 Captura Manual", 
                                           command=self.capturar_manual,
                                           bg='#9B59B6', fg='white', font=("Arial", 11, "bold"),
                                           padx=20, pady=10, cursor='hand2', state='disabled')
        self.btn_captura_manual.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        
        # Configurar peso de columnas
        frame_control.grid_columnconfigure(0, weight=1)
        frame_control.grid_columnconfigure(1, weight=1)
        
        # === SECCIÓN DE ESTADÍSTICAS ===
        frame_estadisticas = tk.LabelFrame(frame_derecho, text="📊 Estadísticas", 
                                          font=("Arial", 12, "bold"), bg='#34495E', 
                                          fg='white', padx=15, pady=15)
        frame_estadisticas.pack(fill=tk.X, pady=(0, 10))
        
        # Estado actual
        frame_estado = tk.Frame(frame_estadisticas, bg='#34495E')
        frame_estado.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(frame_estado, text="Estado:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(side=tk.LEFT)
        
        self.label_estado = tk.Label(frame_estado, text="⚫ Detenido", 
                                     font=("Arial", 10, "bold"), bg='#34495E', 
                                     fg='#E74C3C')
        self.label_estado.pack(side=tk.LEFT, padx=10)
        
        # Grid de estadísticas
        stats_frame = tk.Frame(frame_estadisticas, bg='#34495E')
        stats_frame.pack(fill=tk.X)
        
        # Movimientos detectados
        mov_frame = tk.Frame(stats_frame, bg='#2C3E50', relief=tk.RAISED, borderwidth=2)
        mov_frame.pack(fill=tk.X, pady=5)
        
        self.label_movimientos = tk.Label(mov_frame, text="0", 
                                         font=("Arial", 24, "bold"), 
                                         bg='#2C3E50', fg='#3498DB')
        self.label_movimientos.pack()
        
        tk.Label(mov_frame, text="Movimientos Detectados", 
                font=("Arial", 9), bg='#2C3E50', fg='#BDC3C7').pack()
        
        # Capturas guardadas
        cap_frame = tk.Frame(stats_frame, bg='#2C3E50', relief=tk.RAISED, borderwidth=2)
        cap_frame.pack(fill=tk.X, pady=5)
        
        self.label_capturas = tk.Label(cap_frame, text="0", 
                                       font=("Arial", 24, "bold"), 
                                       bg='#2C3E50', fg='#27AE60')
        self.label_capturas.pack()
        
        tk.Label(cap_frame, text="Capturas Guardadas", 
                font=("Arial", 9), bg='#2C3E50', fg='#BDC3C7').pack()
        
        # === SECCIÓN DE CONFIGURACIÓN ===
        frame_config = tk.LabelFrame(frame_derecho, text="🔧 Configuración", 
                                    font=("Arial", 12, "bold"), bg='#34495E', 
                                    fg='white', padx=15, pady=15)
        frame_config.pack(fill=tk.X, pady=(0, 10))
        
        # Advertencia
        self.label_advertencia = tk.Label(frame_config, 
                                         text="⚠️ Solo editable cuando está detenido", 
                                         font=("Arial", 8, "italic"), 
                                         bg='#34495E', fg='#F39C12')
        self.label_advertencia.pack(anchor='w', pady=(0, 10))
        
        # Sensibilidad
        tk.Label(frame_config, text="Sensibilidad:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        self.slider_sensibilidad = tk.Scale(frame_config, from_=500, to=10000, 
                                           orient=tk.HORIZONTAL, bg='#34495E', 
                                           fg='white', highlightthickness=0,
                                           command=self.cambiar_sensibilidad)
        self.slider_sensibilidad.set(2500)
        self.slider_sensibilidad.pack(fill=tk.X, pady=(0, 10))
        
        # Calidad de compresión
        tk.Label(frame_config, text="Calidad JPEG:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        self.slider_calidad = tk.Scale(frame_config, from_=50, to=100, 
                                      orient=tk.HORIZONTAL, bg='#34495E', 
                                      fg='white', highlightthickness=0,
                                      command=self.cambiar_calidad)
        self.slider_calidad.set(75)
        self.slider_calidad.pack(fill=tk.X, pady=(0, 10))
        
        # Resolución de capturas
        tk.Label(frame_config, text="Resolución:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        resoluciones_frame = tk.Frame(frame_config, bg='#34495E')
        resoluciones_frame.pack(fill=tk.X)
        
        self.resolucion_var = tk.StringVar(value="1280x720")
        resoluciones = [("HD (1280x720)", "1280x720"), 
                       ("Full HD (1920x1080)", "1920x1080"),
                       ("SD (640x480)", "640x480")]
        
        for texto, valor in resoluciones:
            rb = tk.Radiobutton(resoluciones_frame, text=texto, variable=self.resolucion_var,
                              value=valor, bg='#34495E', fg='white', 
                              selectcolor='#2C3E50', command=self.cambiar_resolucion)
            rb.pack(anchor='w')
        
        # === SECCIÓN DE EVENTOS ===
        frame_eventos = tk.LabelFrame(frame_derecho, text="📝 Eventos Recientes", 
                                     font=("Arial", 12, "bold"), bg='#34495E', 
                                     fg='white', padx=15, pady=15)
        frame_eventos.pack(fill=tk.BOTH, expand=True)
        
        self.text_eventos = scrolledtext.ScrolledText(frame_eventos, height=8, 
                                                      wrap=tk.WORD, bg='#2C3E50', 
                                                      fg='white', font=("Consolas", 9),
                                                      relief=tk.FLAT)
        self.text_eventos.pack(fill=tk.BOTH, expand=True)
    
    def bloquear_configuracion(self):
        """Bloquea los controles de configuración."""
        self.slider_sensibilidad.config(state='disabled')
        self.slider_calidad.config(state='disabled')
        for widget in self.ventana.winfo_children():
            self._deshabilitar_radiobuttons(widget)
    
    def desbloquear_configuracion(self):
        """Desbloquea los controles de configuración."""
        self.slider_sensibilidad.config(state='normal')
        self.slider_calidad.config(state='normal')
        for widget in self.ventana.winfo_children():
            self._habilitar_radiobuttons(widget)
    
    def _deshabilitar_radiobuttons(self, widget):
        """Recursivamente deshabilita todos los radiobuttons."""
        if isinstance(widget, tk.Radiobutton):
            widget.config(state='disabled')
        for child in widget.winfo_children():
            self._deshabilitar_radiobuttons(child)
    
    def _habilitar_radiobuttons(self, widget):
        """Recursivamente habilita todos los radiobuttons."""
        if isinstance(widget, tk.Radiobutton):
            widget.config(state='normal')
        for child in widget.winfo_children():
            self._habilitar_radiobuttons(child)
    
    def actualizar_video(self):
        """Actualiza el frame de video en el canvas."""
        frame = self.detector.obtener_frame_actual()
        
        if frame is not None:
            # Agregar información al frame
            stats = self.detector.obtener_estadisticas()
            
            # Texto de información
            cv2.putText(frame, f"Movimientos: {stats['movimientos_detectados']}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Capturas: {stats['capturas_guardadas']}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if stats['cooldown_activo']:
                tiempo_restante = int(stats['tiempo_restante_cooldown'])
                cv2.putText(frame, f"Cooldown: {tiempo_restante}s", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            # Convertir de BGR a RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Redimensionar para ajustar al canvas
            height, width = frame_rgb.shape[:2]
            max_width = 800
            max_height = 600
            
            scale = min(max_width/width, max_height/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
            
            # Convertir a ImageTk
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Actualizar canvas
            self.canvas_video.create_image(400, 300, image=imgtk, anchor=tk.CENTER)
            self.canvas_video.image = imgtk
        
        # Programar siguiente actualización
        self.ventana.after(33, self.actualizar_video)  # ~30 FPS
    
    def actualizar_estadisticas(self):
        """Actualiza las estadísticas en la interfaz."""
        stats = self.detector.obtener_estadisticas()
        
        # Actualizar labels
        self.label_movimientos.config(text=str(stats['movimientos_detectados']))
        self.label_capturas.config(text=str(stats['capturas_guardadas']))
        
        # Actualizar estado
        if stats['estado'] == 'ejecutando':
            if stats['pausado']:
                self.label_estado.config(text="⏸️ Pausado", fg='#F39C12')
            else:
                self.label_estado.config(text="🟢 Activo", fg='#27AE60')
        else:
            self.label_estado.config(text="⚫ Detenido", fg='#E74C3C')
        
        # Programar siguiente actualización
        self.ventana.after(1000, self.actualizar_estadisticas)  # Cada segundo
    
    def procesar_eventos(self):
        """Procesa eventos de la cola del detector."""
        evento = self.detector.obtener_evento()
        
        while evento:
            timestamp = time.strftime("%H:%M:%S")
            
            if evento['tipo'] == 'captura':
                tipo_texto = "📸 MANUAL" if evento.get('tipo_captura') == 'manual' else "🔴 AUTO"
                mensaje = f"[{timestamp}] {tipo_texto} - {evento['archivo']} ({evento['tamaño_kb']} KB)\n"
                self.agregar_evento(mensaje, 'success')
            elif evento['tipo'] == 'error':
                mensaje = f"[{timestamp}] ⚠️ Error: {evento['mensaje']}\n"
                self.agregar_evento(mensaje, 'error')
            else:
                mensaje = f"[{timestamp}] ℹ️ {evento['mensaje']}\n"
                self.agregar_evento(mensaje, 'info')
            
            evento = self.detector.obtener_evento()
        
        # Programar siguiente comprobación
        self.ventana.after(500, self.procesar_eventos)
    
    def agregar_evento(self, mensaje, tipo='info'):
        """Agrega un evento al área de texto."""
        self.text_eventos.insert(tk.END, mensaje)
        
        # Mantener solo últimas 100 líneas
        lineas = int(self.text_eventos.index('end-1c').split('.')[0])
        if lineas > 100:
            self.text_eventos.delete('1.0', '2.0')
        
        # Auto-scroll al final
        self.text_eventos.see(tk.END)
    
    def iniciar_detector(self):
        """Inicia el detector."""
        if self.detector.iniciar():
            self.btn_iniciar.config(state='disabled')
            self.btn_detener.config(state='normal')
            self.btn_pausar.config(state='normal')
            self.btn_captura_manual.config(state='normal')
            self.bloquear_configuracion()
            self.agregar_evento("[INFO] Detector iniciado\n", 'info')
        else:
            messagebox.showerror("Error", "No se pudo iniciar el detector")
            self.agregar_evento("[ERROR] No se pudo iniciar el detector\n", 'error')
    
    def detener_detector(self):
        """Detiene el detector."""
        self.detector.detener()
        self.btn_iniciar.config(state='normal')
        self.btn_detener.config(state='disabled')
        self.btn_pausar.config(state='disabled')
        self.btn_reanudar.config(state='disabled')
        self.btn_captura_manual.config(state='disabled')
        self.desbloquear_configuracion()
        self.agregar_evento("[INFO] Detector detenido\n", 'info')
    
    def pausar_detector(self):
        """Pausa el detector."""
        self.detector.pausar()
        self.btn_pausar.config(state='disabled')
        self.btn_reanudar.config(state='normal')
        self.btn_captura_manual.config(state='disabled')
        self.agregar_evento("[INFO] Detección pausada\n", 'info')
    
    def reanudar_detector(self):
        """Reanuda el detector."""
        self.detector.reanudar()
        self.btn_pausar.config(state='normal')
        self.btn_reanudar.config(state='disabled')
        self.btn_captura_manual.config(state='normal')
        self.agregar_evento("[INFO] Detección reanudada\n", 'info')
    
    def capturar_manual(self):
        """Solicita una captura manual."""
        if self.detector.capturar_manual():
            self.agregar_evento("[INFO] Captura manual en proceso...\n", 'info')
        else:
            messagebox.showwarning("Advertencia", "El detector debe estar activo para capturar manualmente")
    
    def cambiar_sensibilidad(self, valor):
        """Cambia la sensibilidad del detector."""
        if not self.detector.configurar_sensibilidad(int(valor)):
            self.agregar_evento("[WARN] No se puede cambiar sensibilidad mientras está activo\n", 'error')
    
    def cambiar_calidad(self, valor):
        """Cambia la calidad de compresión."""
        config = self.detector.obtener_configuracion()
        if not self.detector.configurar_compresion(calidad=int(valor), resolucion=config['resolucion']):
            self.agregar_evento("[WARN] No se puede cambiar calidad mientras está activo\n", 'error')
    
    def cambiar_resolucion(self):
        """Cambia la resolución de las capturas."""
        resolucion_str = self.resolucion_var.get()
        width, height = map(int, resolucion_str.split('x'))
        config = self.detector.obtener_configuracion()
        if not self.detector.configurar_compresion(calidad=config['calidad_jpeg'], resolucion=(width, height)):
            self.agregar_evento("[WARN] No se puede cambiar resolución mientras está activo\n", 'error')
    
    def cerrar_aplicacion(self):
        """Cierra limpiamente la aplicación."""
        if messagebox.askokcancel("Salir", "¿Deseas cerrar la aplicación?"):
            self.detector.detener()
            time.sleep(0.5)  # Esperar a que se detenga
            self.ventana.destroy()


if __name__ == "__main__":
    ventana = tk.Tk()
    app = AplicacionDetector(ventana)
    ventana.mainloop()
