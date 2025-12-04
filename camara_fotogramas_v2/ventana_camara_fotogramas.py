"""
Ventana de Control de Cámara de Fotogramas
Módulo para integrar en la aplicación principal
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import cv2
from PIL import Image, ImageTk
from detector_movimiento_v2 import DetectorMovimiento
import time


class VentanaCamaraFotogramas:
    """
    Ventana independiente para controlar una cámara de fotogramas.
    Se puede abrir desde la app principal cuando se edita un dispositivo tipo 'camara_fotogramas'.
    """
    
    def __init__(self, ventana_padre, dispositivo_id, nombre_dispositivo, callback_guardar=None):
        """
        Inicializa la ventana de control de cámara.
        
        Args:
            ventana_padre: Ventana principal de la aplicación
            dispositivo_id: ID del dispositivo en la base de datos
            nombre_dispositivo: Nombre del dispositivo
            callback_guardar: Función a llamar cuando se guarde la configuración
        """
        self.ventana_padre = ventana_padre
        self.dispositivo_id = dispositivo_id
        self.nombre_dispositivo = nombre_dispositivo
        self.callback_guardar = callback_guardar
        
        # Crear ventana toplevel
        self.ventana = tk.Toplevel(ventana_padre)
        self.ventana.title(f"🎥 Control de Cámara - {nombre_dispositivo}")
        self.ventana.geometry("1200x750")
        self.ventana.configure(bg='#2C3E50')
        
        # Hacer la ventana modal
        self.ventana.transient(ventana_padre)
        self.ventana.grab_set()
        
        # Crear detector
        self.detector = DetectorMovimiento(
            carpeta_capturas=f"capturas_{dispositivo_id}",
            carpeta_historial=f"historial_{dispositivo_id}"
        )
        
        # Configuración del dispositivo (se cargará desde BD)
        self.config = {
            'indice_camara': 0,
            'sensibilidad': 2500,
            'calidad_jpeg': 75,
            'resolucion': (1280, 720),
            'cooldown': 5,
            'activo': False
        }
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Iniciar actualizaciones
        self.actualizar_video()
        self.actualizar_estadisticas()
        self.procesar_eventos()
        
        # Manejar cierre de ventana
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
    
    def cargar_configuracion(self, config):
        """
        Carga la configuración desde la base de datos.
        
        Args:
            config: Diccionario con la configuración guardada
        """
        self.config.update(config)
        
        # Aplicar configuración al detector
        self.detector.configurar_sensibilidad(self.config['sensibilidad'])
        self.detector.configurar_compresion(
            calidad=self.config['calidad_jpeg'],
            resolucion=self.config['resolucion']
        )
        self.detector.configurar_cooldown(self.config['cooldown'])
        
        # Actualizar controles de la interfaz
        self.slider_sensibilidad.set(self.config['sensibilidad'])
        self.slider_calidad.set(self.config['calidad_jpeg'])
        self.slider_cooldown.set(self.config['cooldown'])
        
        # Seleccionar resolución
        resolucion_str = f"{self.config['resolucion'][0]}x{self.config['resolucion'][1]}"
        self.resolucion_var.set(resolucion_str)
    
    def obtener_configuracion(self):
        """
        Obtiene la configuración actual para guardar en BD.
        
        Returns:
            dict: Configuración actual
        """
        stats = self.detector.obtener_estadisticas()
        
        return {
            'indice_camara': self.config['indice_camara'],
            'sensibilidad': self.config['sensibilidad'],
            'calidad_jpeg': self.config['calidad_jpeg'],
            'resolucion': self.config['resolucion'],
            'cooldown': self.config['cooldown'],
            'activo': stats['estado'] == 'ejecutando',
            'estadisticas': {
                'movimientos_detectados': stats['movimientos_detectados'],
                'capturas_guardadas': stats['capturas_guardadas']
            }
        }
    
    def crear_interfaz(self):
        """Crea la interfaz de la ventana."""
        # Frame principal
        frame_principal = tk.Frame(self.ventana, bg='#2C3E50')
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ===== LADO IZQUIERDO: VIDEO =====
        frame_izquierdo = tk.Frame(frame_principal, bg='#2C3E50')
        frame_izquierdo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Título
        titulo = tk.Label(frame_izquierdo, 
                         text=f"📹 {self.nombre_dispositivo}", 
                         font=("Arial", 16, "bold"), bg='#2C3E50', fg='white')
        titulo.pack(pady=(0, 10))
        
        # Canvas para el video
        self.canvas_video = tk.Canvas(frame_izquierdo, width=800, height=600, 
                                      bg='black', highlightthickness=2, 
                                      highlightbackground='#3498DB')
        self.canvas_video.pack()
        
        # ===== LADO DERECHO: CONTROLES =====
        frame_derecho = tk.Frame(frame_principal, bg='#2C3E50', width=350)
        frame_derecho.pack(side=tk.RIGHT, fill=tk.BOTH)
        frame_derecho.pack_propagate(False)
        
        # === CONTROL ===
        frame_control = tk.LabelFrame(frame_derecho, text="⚙️ Control", 
                                     font=("Arial", 12, "bold"), bg='#34495E', 
                                     fg='white', padx=15, pady=15)
        frame_control.pack(fill=tk.X, pady=(0, 10))
        
        # Botones
        self.btn_iniciar = tk.Button(frame_control, text="▶️ Iniciar", 
                                     command=self.iniciar_detector,
                                     bg='#27AE60', fg='white', font=("Arial", 11, "bold"),
                                     padx=20, pady=10)
        self.btn_iniciar.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        self.btn_detener = tk.Button(frame_control, text="⏹️ Detener", 
                                     command=self.detener_detector,
                                     bg='#E74C3C', fg='white', font=("Arial", 11, "bold"),
                                     padx=20, pady=10, state='disabled')
        self.btn_detener.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.btn_pausar = tk.Button(frame_control, text="⏸️ Pausar", 
                                   command=self.pausar_detector,
                                   bg='#F39C12', fg='white', font=("Arial", 11, "bold"),
                                   padx=20, pady=10, state='disabled')
        self.btn_pausar.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        
        self.btn_reanudar = tk.Button(frame_control, text="▶️ Reanudar", 
                                     command=self.reanudar_detector,
                                     bg='#16A085', fg='white', font=("Arial", 11, "bold"),
                                     padx=20, pady=10, state='disabled')
        self.btn_reanudar.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Separator(frame_control, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        
        self.btn_captura_manual = tk.Button(frame_control, text="📸 Captura Manual", 
                                           command=self.capturar_manual,
                                           bg='#9B59B6', fg='white', font=("Arial", 11, "bold"),
                                           padx=20, pady=10, state='disabled')
        self.btn_captura_manual.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        
        frame_control.grid_columnconfigure(0, weight=1)
        frame_control.grid_columnconfigure(1, weight=1)
        
        # === ESTADÍSTICAS ===
        frame_stats = tk.LabelFrame(frame_derecho, text="📊 Estadísticas", 
                                   font=("Arial", 12, "bold"), bg='#34495E', 
                                   fg='white', padx=15, pady=15)
        frame_stats.pack(fill=tk.X, pady=(0, 10))
        
        # Estado
        frame_estado = tk.Frame(frame_stats, bg='#34495E')
        frame_estado.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(frame_estado, text="Estado:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(side=tk.LEFT)
        
        self.label_estado = tk.Label(frame_estado, text="⚫ Detenido", 
                                     font=("Arial", 10, "bold"), bg='#34495E', 
                                     fg='#E74C3C')
        self.label_estado.pack(side=tk.LEFT, padx=10)
        
        # Contadores
        stats_grid = tk.Frame(frame_stats, bg='#34495E')
        stats_grid.pack(fill=tk.X)
        
        mov_frame = tk.Frame(stats_grid, bg='#2C3E50', relief=tk.RAISED, borderwidth=2)
        mov_frame.pack(fill=tk.X, pady=5)
        
        self.label_movimientos = tk.Label(mov_frame, text="0", 
                                         font=("Arial", 24, "bold"), 
                                         bg='#2C3E50', fg='#3498DB')
        self.label_movimientos.pack()
        
        tk.Label(mov_frame, text="Movimientos", 
                font=("Arial", 9), bg='#2C3E50', fg='#BDC3C7').pack()
        
        cap_frame = tk.Frame(stats_grid, bg='#2C3E50', relief=tk.RAISED, borderwidth=2)
        cap_frame.pack(fill=tk.X, pady=5)
        
        self.label_capturas = tk.Label(cap_frame, text="0", 
                                       font=("Arial", 24, "bold"), 
                                       bg='#2C3E50', fg='#27AE60')
        self.label_capturas.pack()
        
        tk.Label(cap_frame, text="Capturas", 
                font=("Arial", 9), bg='#2C3E50', fg='#BDC3C7').pack()
        
        # === CONFIGURACIÓN ===
        frame_config = tk.LabelFrame(frame_derecho, text="🔧 Configuración", 
                                    font=("Arial", 12, "bold"), bg='#34495E', 
                                    fg='white', padx=15, pady=15)
        frame_config.pack(fill=tk.X, pady=(0, 10))
        
        # Advertencia
        tk.Label(frame_config, text="⚠️ Solo editable cuando está detenido", 
                font=("Arial", 8, "italic"), bg='#34495E', fg='#F39C12').pack(anchor='w', pady=(0, 10))
        
        # Sensibilidad
        tk.Label(frame_config, text="Sensibilidad:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        self.slider_sensibilidad = tk.Scale(frame_config, from_=500, to=10000, 
                                           orient=tk.HORIZONTAL, bg='#34495E', 
                                           fg='white', command=self.cambiar_sensibilidad)
        self.slider_sensibilidad.set(2500)
        self.slider_sensibilidad.pack(fill=tk.X, pady=(0, 10))
        
        # Calidad
        tk.Label(frame_config, text="Calidad JPEG:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        self.slider_calidad = tk.Scale(frame_config, from_=50, to=100, 
                                      orient=tk.HORIZONTAL, bg='#34495E', 
                                      fg='white', command=self.cambiar_calidad)
        self.slider_calidad.set(75)
        self.slider_calidad.pack(fill=tk.X, pady=(0, 10))
        
        # Cooldown
        tk.Label(frame_config, text="Cooldown (segundos):", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        self.slider_cooldown = tk.Scale(frame_config, from_=1, to=30, 
                                       orient=tk.HORIZONTAL, bg='#34495E', 
                                       fg='white', command=self.cambiar_cooldown)
        self.slider_cooldown.set(5)
        self.slider_cooldown.pack(fill=tk.X, pady=(0, 10))
        
        # Resolución
        tk.Label(frame_config, text="Resolución:", font=("Arial", 10), 
                bg='#34495E', fg='white').pack(anchor='w')
        
        self.resolucion_var = tk.StringVar(value="1280x720")
        resoluciones = [("HD (1280x720)", "1280x720"), 
                       ("Full HD (1920x1080)", "1920x1080"),
                       ("SD (640x480)", "640x480")]
        
        for texto, valor in resoluciones:
            rb = tk.Radiobutton(frame_config, text=texto, variable=self.resolucion_var,
                              value=valor, bg='#34495E', fg='white', 
                              selectcolor='#2C3E50', command=self.cambiar_resolucion)
            rb.pack(anchor='w')
        
        # === EVENTOS ===
        frame_eventos = tk.LabelFrame(frame_derecho, text="📝 Eventos", 
                                     font=("Arial", 12, "bold"), bg='#34495E', 
                                     fg='white', padx=15, pady=15)
        frame_eventos.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_eventos = scrolledtext.ScrolledText(frame_eventos, height=6, 
                                                      wrap=tk.WORD, bg='#2C3E50', 
                                                      fg='white', font=("Consolas", 9))
        self.text_eventos.pack(fill=tk.BOTH, expand=True)
        
        # === BOTONES DE ACCIÓN ===
        frame_acciones = tk.Frame(frame_derecho, bg='#2C3E50')
        frame_acciones.pack(fill=tk.X)
        
        btn_guardar = tk.Button(frame_acciones, text="💾 Guardar y Cerrar", 
                               command=self.guardar_y_cerrar,
                               bg='#27AE60', fg='white', font=("Arial", 11, "bold"),
                               padx=20, pady=10)
        btn_guardar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        btn_cancelar = tk.Button(frame_acciones, text="❌ Cancelar", 
                                command=self.cerrar_ventana,
                                bg='#E74C3C', fg='white', font=("Arial", 11, "bold"),
                                padx=20, pady=10)
        btn_cancelar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
    
    # [Métodos de control - iguales que antes]
    def bloquear_config(self):
        self.slider_sensibilidad.config(state='disabled')
        self.slider_calidad.config(state='disabled')
        self.slider_cooldown.config(state='disabled')
        for widget in self.ventana.winfo_children():
            self._toggle_radiobuttons(widget, False)
    
    def desbloquear_config(self):
        self.slider_sensibilidad.config(state='normal')
        self.slider_calidad.config(state='normal')
        self.slider_cooldown.config(state='normal')
        for widget in self.ventana.winfo_children():
            self._toggle_radiobuttons(widget, True)
    
    def _toggle_radiobuttons(self, widget, enable):
        if isinstance(widget, tk.Radiobutton):
            widget.config(state='normal' if enable else 'disabled')
        for child in widget.winfo_children():
            self._toggle_radiobuttons(child, enable)
    
    def actualizar_video(self):
        frame = self.detector.obtener_frame_actual()
        
        if frame is not None:
            stats = self.detector.obtener_estadisticas()
            cv2.putText(frame, f"Movimientos: {stats['movimientos_detectados']}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Capturas: {stats['capturas_guardadas']}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if stats['cooldown_activo']:
                tiempo_restante = int(stats['tiempo_restante_cooldown'])
                cv2.putText(frame, f"Cooldown: {tiempo_restante}s", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width = frame_rgb.shape[:2]
            scale = min(800/width, 600/height)
            new_width, new_height = int(width * scale), int(height * scale)
            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
            
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas_video.create_image(400, 300, image=imgtk, anchor=tk.CENTER)
            self.canvas_video.image = imgtk
        
        if self.ventana.winfo_exists():
            self.ventana.after(33, self.actualizar_video)
    
    def actualizar_estadisticas(self):
        stats = self.detector.obtener_estadisticas()
        self.label_movimientos.config(text=str(stats['movimientos_detectados']))
        self.label_capturas.config(text=str(stats['capturas_guardadas']))
        
        if stats['estado'] == 'ejecutando':
            if stats['pausado']:
                self.label_estado.config(text="⏸️ Pausado", fg='#F39C12')
            else:
                self.label_estado.config(text="🟢 Activo", fg='#27AE60')
        else:
            self.label_estado.config(text="⚫ Detenido", fg='#E74C3C')
        
        if self.ventana.winfo_exists():
            self.ventana.after(1000, self.actualizar_estadisticas)
    
    def procesar_eventos(self):
        evento = self.detector.obtener_evento()
        
        while evento:
            timestamp = time.strftime("%H:%M:%S")
            if evento['tipo'] == 'captura':
                tipo_texto = "📸 MANUAL" if evento.get('tipo_captura') == 'manual' else "🔴 AUTO"
                mensaje = f"[{timestamp}] {tipo_texto} - {evento['archivo']}\n"
            elif evento['tipo'] == 'error':
                mensaje = f"[{timestamp}] ⚠️ {evento['mensaje']}\n"
            else:
                mensaje = f"[{timestamp}] ℹ️ {evento['mensaje']}\n"
            
            self.text_eventos.insert(tk.END, mensaje)
            self.text_eventos.see(tk.END)
            evento = self.detector.obtener_evento()
        
        if self.ventana.winfo_exists():
            self.ventana.after(500, self.procesar_eventos)
    
    def iniciar_detector(self):
        if self.detector.iniciar(self.config['indice_camara']):
            self.btn_iniciar.config(state='disabled')
            self.btn_detener.config(state='normal')
            self.btn_pausar.config(state='normal')
            self.btn_captura_manual.config(state='normal')
            self.bloquear_config()
    
    def detener_detector(self):
        self.detector.detener()
        self.btn_iniciar.config(state='normal')
        self.btn_detener.config(state='disabled')
        self.btn_pausar.config(state='disabled')
        self.btn_reanudar.config(state='disabled')
        self.btn_captura_manual.config(state='disabled')
        self.desbloquear_config()
    
    def pausar_detector(self):
        self.detector.pausar()
        self.btn_pausar.config(state='disabled')
        self.btn_reanudar.config(state='normal')
        self.btn_captura_manual.config(state='disabled')
    
    def reanudar_detector(self):
        self.detector.reanudar()
        self.btn_pausar.config(state='normal')
        self.btn_reanudar.config(state='disabled')
        self.btn_captura_manual.config(state='normal')
    
    def capturar_manual(self):
        self.detector.capturar_manual()
    
    def cambiar_sensibilidad(self, valor):
        self.config['sensibilidad'] = int(valor)
        self.detector.configurar_sensibilidad(int(valor))
    
    def cambiar_calidad(self, valor):
        self.config['calidad_jpeg'] = int(valor)
        self.detector.configurar_compresion(calidad=int(valor), resolucion=self.config['resolucion'])
    
    def cambiar_cooldown(self, valor):
        self.config['cooldown'] = int(valor)
        self.detector.configurar_cooldown(int(valor))
    
    def cambiar_resolucion(self):
        resolucion_str = self.resolucion_var.get()
        width, height = map(int, resolucion_str.split('x'))
        self.config['resolucion'] = (width, height)
        self.detector.configurar_compresion(calidad=self.config['calidad_jpeg'], resolucion=(width, height))
    
    def guardar_y_cerrar(self):
        """Guarda la configuración y cierra la ventana."""
        config_actual = self.obtener_configuracion()
        
        if self.callback_guardar:
            self.callback_guardar(self.dispositivo_id, config_actual)
        
        self.cerrar_ventana()
    
    def cerrar_ventana(self):
        """Cierra la ventana limpiamente."""
        self.detector.detener()
        time.sleep(0.3)
        self.ventana.destroy()


# Ejemplo de integración en la app principal
def ejemplo_integracion():
    """
    Ejemplo de cómo abrir esta ventana desde la app principal.
    """
    
    def callback_guardar(dispositivo_id, config):
        print(f"Guardando configuración del dispositivo {dispositivo_id}:")
        print(config)
        # Aquí guardarías en tu base de datos
    
    # Crear ventana principal de prueba
    root = tk.Tk()
    root.title("App Principal")
    root.geometry("400x300")
    
    def abrir_control_camara():
        # Esto es lo que llamarías cuando el usuario hace clic en "Editar" 
        # para un dispositivo de tipo "camara_fotogramas"
        ventana = VentanaCamaraFotogramas(
            ventana_padre=root,
            dispositivo_id=1,
            nombre_dispositivo="Cámara Entrada",
            callback_guardar=callback_guardar
        )
        
        # Si quieres cargar configuración guardada:
        config_guardada = {
            'indice_camara': 0,
            'sensibilidad': 3000,
            'calidad_jpeg': 80,
            'resolucion': (1920, 1080),
            'cooldown': 7
        }
        ventana.cargar_configuracion(config_guardada)
    
    # Botón de prueba
    btn = tk.Button(root, text="Abrir Control de Cámara", 
                   command=abrir_control_camara,
                   font=("Arial", 12), padx=20, pady=10)
    btn.pack(expand=True)
    
    root.mainloop()


if __name__ == "__main__":
    ejemplo_integracion()
