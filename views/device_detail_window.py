"""
Ventana de detalle para ver y editar información de un dispositivo
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import time
from config import COLORS
import cv2
from PIL import Image, ImageTk
from controllers.serial_comm import get_serial_communicator
from pathlib import Path
import os
import sys
import subprocess


class DeviceDetailWindow(tk.Toplevel):
    """Ventana toplevel para mostrar y editar detalles de un dispositivo"""
    
    def __init__(self, master, device, device_manager, refresh_callback, tipos_list):
        """
        Args:
            master: widget padre (usualmente la app o el frame principal)
            device: dict con keys id, tipo, zona, etc.
            device_manager: instancia DeviceManager
            refresh_callback: función para refrescar la vista principal (DevicesFrame)
            tipos_list: lista de tipos permitidos (ordenada)
        """
        super().__init__(master)
        self.title(f"Detalles - {device['id']}")
        self.geometry("650x850")  # Mayor altura para dispositivos con cámara
        self.config(bg=COLORS["background"])
        self.device = device
        self.device_manager = device_manager
        self.refresh_callback = refresh_callback
        self.tipos_list = tipos_list
        self.day_buttons = {}
        self.hour_buttons = {}
        self.active = device.get("active", False)
        
        # Comunicador serial
        self.serial_comm = get_serial_communicator()

        # --- Scroll principal ---
        main_canvas = tk.Canvas(self, bg=COLORS["background"], highlightthickness=0)
        main_canvas.pack(side="left", fill="both", expand=True)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=main_canvas.yview)
        v_scroll.pack(side="right", fill="y")
        main_canvas.configure(yscrollcommand=v_scroll.set)

        content = tk.Frame(main_canvas, bg=COLORS["background"])
        window_id = main_canvas.create_window((0, 0), window=content, anchor="nw")

        def on_configure(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        content.bind("<Configure>", on_configure)
        main_canvas.bind("<Configure>", lambda e: main_canvas.itemconfigure(window_id, width=e.width))

        # --- Botón Volver ---
        tk.Button(
            content, 
            text="← Volver", 
            font=("Arial", 10, "bold"),
            bg=COLORS["accent"], 
            fg="white", 
            relief="flat", 
            command=self._on_close
        ).pack(pady=10)

        # --- ID editable ---
        self.id_var = tk.StringVar(value=self.device["id"])
        tk.Label(
            content, 
            text="ID:", 
            bg=COLORS["background"], 
            font=("Arial", 12, "bold")
        ).pack()
        
        id_frame = tk.Frame(content, bg=COLORS["background"])
        id_frame.pack(pady=5)
        self.id_label = tk.Label(
            id_frame, 
            textvariable=self.id_var, 
            bg=COLORS["background"], 
            font=("Arial", 12)
        )
        self.id_label.pack(side="left", padx=5)
        tk.Button(
            id_frame, 
            text="Editar", 
            bg=COLORS["danger"], 
            fg="white", 
            relief="flat",
            font=("Arial", 10), 
            command=self._edit_id
        ).pack(side="left", padx=10)

        # --- Tipo (dropdown) ---
        tk.Label(
            content, 
            text="Tipo de dispositivo:", 
            bg=COLORS["background"], 
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 2))
        
        self.tipo_var = tk.StringVar(value=self.device["tipo"])
        tipo_menu = ttk.OptionMenu(
            content, 
            self.tipo_var, 
            self.device["tipo"], 
            *self.tipos_list,
            command=self._on_tipo_changed
        )
        tipo_menu.pack(pady=5)

        # --- Zona (dropdown) ---
        tk.Label(
            content, 
            text="Zona:", 
            bg=COLORS["background"], 
            font=("Arial", 12, "bold")
        ).pack(pady=(15, 2))
        
        zonas = self.device_manager.get_zones()
        if self.device["zona"] not in zonas:
            zonas.append(self.device["zona"])
        zonas = sorted(zonas)
        self.zona_var = tk.StringVar(value=self.device["zona"])
        zona_menu = ttk.OptionMenu(
            content, 
            self.zona_var, 
            self.device["zona"], 
            *zonas, 
            command=self._on_zone_changed
        )
        zona_menu.pack(pady=5)

        # --- Activar / Desactivar ---
        self.state_button = tk.Button(
            content, 
            text="Activado" if self.active else "Desactivado",
            bg=COLORS["accent"] if self.active else COLORS["danger"],
            fg=COLORS["text_light"], 
            font=("Arial", 12, "bold"),
            width=15, 
            command=self._toggle_state
        )
        self.state_button.pack(pady=12)
        
        # --- Controles especiales según tipo de dispositivo ---
        self._add_special_controls(content)

        # --- Historial específico ---
        tk.Label(
            content, 
            text="Historial específico", 
            bg=COLORS["background"],
            font=("Arial", 13, "bold")
        ).pack(pady=(8, 0))
        
        hist_frame = tk.Frame(content, bg=COLORS["background"])
        hist_frame.pack(pady=6, padx=20, fill="both")
        self.hist_text = scrolledtext.ScrolledText(
            hist_frame, 
            width=70, 
            height=6, 
            state="disabled", 
            wrap=tk.WORD
        )
        self.hist_text.pack(fill="both", expand=True)

        # --- Horarios activos ---
        tk.Label(
            content, 
            text="Horarios Activos", 
            bg=COLORS["background"], 
            font=("Arial", 13, "bold")
        ).pack(pady=(12, 4))

        # Días
        tk.Label(
            content, 
            text="Días:", 
            bg=COLORS["background"], 
            font=("Arial", 12, "bold")
        ).pack()
        
        days_frame = tk.Frame(content, bg=COLORS["background"])
        days_frame.pack(pady=6)
        days = ["L", "M", "X", "J", "V", "S", "D"]
        for d in days:
            b = tk.Button(
                days_frame, 
                text=d, 
                width=3, 
                height=1, 
                font=("Arial", 10, "bold"),
                relief="flat", 
                bg="lightgray", 
                fg="black", 
                bd=1,
                command=lambda _d=d: self._toggle_day(_d)
            )
            b.pack(side="left", padx=8, pady=4)
            self._make_circle(b)
            self.day_buttons[d] = b

        # Horas en 4 filas x 6 columnas (0..23)
        tk.Label(
            content, 
            text="Horas:", 
            bg=COLORS["background"], 
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 4))
        
        hours_container = tk.Frame(content, bg=COLORS["background"])
        hours_container.pack(pady=4)
        hour = 0
        for r in range(4):
            row = tk.Frame(hours_container, bg=COLORS["background"])
            row.pack(pady=4)
            for c in range(6):
                if hour >= 24:
                    break
                hb = tk.Button(
                    row, 
                    text=str(hour), 
                    width=3, 
                    height=1, 
                    font=("Arial", 9),
                    relief="flat", 
                    bg="lightgray", 
                    fg="black", 
                    bd=1,
                    command=lambda h=hour: self._toggle_hour(h)
                )
                hb.pack(side="left", padx=8, pady=2)
                self._make_circle(hb)
                self.hour_buttons[hour] = hb
                hour += 1

        # --- Eliminar dispositivo ---
        tk.Button(
            content, 
            text="Eliminar dispositivo", 
            bg=COLORS["danger"], 
            fg="white",
            font=("Arial", 11, "bold"), 
            relief="flat", 
            command=self._delete_device
        ).pack(pady=20)

        # Aseguramos que el estado visual coincide con el dato inicial
        self._update_state_button()
    
    def _add_special_controls(self, parent):
        """
        Agrega controles especiales según el tipo de dispositivo.
        - Cerradura: botones Abrir/Cerrar
        - Simulador de Presencia: indicador de estado
        """
        tipo = self.device.get("tipo", "").lower()
        
        # --- CERRADURA ---
        if "cerradura" in tipo or "llave" in tipo:
            tk.Label(
                parent, 
                text="Control de Cerradura", 
                bg=COLORS["background"],
                font=("Arial", 13, "bold")
            ).pack(pady=(10, 5))
            
            control_frame = tk.Frame(parent, bg=COLORS["background"])
            control_frame.pack(pady=5)
            
            tk.Button(
                control_frame,
                text="🔓 ABRIR",
                bg="#4CAF50",
                fg="white",
                font=("Arial", 12, "bold"),
                width=12,
                command=self._abrir_cerradura
            ).pack(side="left", padx=10)
            
            tk.Button(
                control_frame,
                text="🔒 CERRAR",
                bg="#f44336",
                fg="white",
                font=("Arial", 12, "bold"),
                width=12,
                command=self._cerrar_cerradura
            ).pack(side="left", padx=10)
            
            # Indicador de estado
            self.cerradura_estado = tk.Label(
                parent,
                text="Estado: Cerrada",
                bg=COLORS["background"],
                font=("Arial", 11),
                fg="#666"
            )
            self.cerradura_estado.pack(pady=5)
        
        # --- SIMULADOR DE PRESENCIA ---
        elif "simulador" in tipo or "presencia" in tipo:
            tk.Label(
                parent, 
                text="💡 Simulador Activo", 
                bg=COLORS["background"],
                font=("Arial", 12, "bold"),
                fg=COLORS["accent"]
            ).pack(pady=10)
            
            tk.Label(
                parent,
                text="El simulador se activa automáticamente\ncuando el dispositivo está encendido",
                bg=COLORS["background"],
                font=("Arial", 10),
                fg="#666",
                justify="center"
            ).pack(pady=5)
        
        # --- DETECTOR DE PLACAS ---
        elif "placa" in tipo or "detector_placa" in tipo or "ocr" in tipo:
            self._crear_controles_detector_placas(parent)

         # --- CÁMARA DE SEGURIDAD ---
        elif "camara" in tipo or "camara_seguridad" in tipo or "fotogramas" in tipo:
            self._crear_controles_camara(parent)
    def _abrir_carpeta_placas(self):
        """Abre la carpeta de capturas de placas"""
        carpeta = "capturas_placas"
        self._abrir_carpeta_sistema(carpeta)
    
    def _ver_galeria_placas(self):
        """Abre ventana de galería para placas"""
        try:
            from views.galeria_window import GaleriaWindow
            GaleriaWindow(self, "capturas_placas", "Galería - Detector de Placas")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir galería:\n{e}")
    
    def _limpiar_capturas_placas(self):
        """Limpia capturas antiguas de placas (más de 30 días)"""
        eliminadas = self._limpiar_capturas_antiguas("capturas_placas", dias=30)
        messagebox.showinfo(
            "Limpieza Completada",
            f"Se eliminaron {eliminadas} capturas con más de 30 días"
        )
        self._actualizar_contador_capturas_placas()
    
    def _actualizar_contador_capturas_placas(self):
        """Actualiza el contador de capturas de placas"""
        carpeta = Path("capturas_placas")
        if carpeta.exists():
            count = len(list(carpeta.glob("*.jpg")))
            self.label_capturas_placas_count.config(text=f"{count} capturas")
        else:
            self.label_capturas_placas_count.config(text="0 capturas")

# === AGREGAR ESTE MÉTODO COMPLETO AL FINAL DE LA CLASE ===

    def _crear_controles_camara(self, parent):
        """Crea los controles para la cámara de seguridad"""
        try:
            from controllers.detector_movimiento_camara import DetectorMovimientoCamara
        except ImportError:
            tk.Label(
                parent,
                text="❌ detector_movimiento_camara.py no encontrado",
                bg=COLORS["background"],
                fg="#f44336"
            ).pack(pady=10)
            return
        
        # Título
        tk.Label(
            parent,
            text="📷 Cámara de Seguridad",
            bg=COLORS["background"],
            font=("Arial", 12, "bold")  # Reducido de 13 a 12
        ).pack(pady=(5, 3))  # Reducido padding
        
        # Frame para video (reducido para que quepa mejor)
        video_frame = tk.Frame(parent, bg="black", width=280, height=210)
        video_frame.pack(pady=3)  # Reducido de 5 a 3
        video_frame.pack_propagate(False)
        
        self.canvas_camara = tk.Canvas(video_frame, width=280, height=210, bg="black")
        self.canvas_camara.pack()
        
        # Estado
        self.label_estado_camara = tk.Label(
            parent,
            text="⚪ Estado: Detenida",
            bg=COLORS["background"],
            font=("Arial", 9),  # Reducido de 10 a 9
            fg="#666"
        )
        self.label_estado_camara.pack(pady=3)  # Reducido de 5 a 3
        
        # Estadísticas
        stats_frame = tk.Frame(parent, bg=COLORS["background"])
        stats_frame.pack(fill="x", padx=10, pady=2)  # Reducido de 5 a 2
        
        self.label_movimientos = tk.Label(
            stats_frame,
            text="Movimientos: 0",
            bg=COLORS["background"],
            font=("Arial", 9),
            fg="#666"
        )
        self.label_movimientos.pack(side="left", padx=5)
        
        self.label_capturas = tk.Label(
            stats_frame,
            text="Capturas: 0",
            bg=COLORS["background"],
            font=("Arial", 9),
            fg="#666"
        )
        self.label_capturas.pack(side="left", padx=5)
        
        # Controles principales
        control_frame = tk.Frame(parent, bg=COLORS["background"])
        control_frame.pack(pady=3)  # Reducido de 5 a 3
        
        self.btn_iniciar_camara = tk.Button(
            control_frame,
            text="▶️ Iniciar",
            command=self._iniciar_camara,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10
        )
        self.btn_iniciar_camara.pack(side="left", padx=5)
        
        self.btn_pausar_camara = tk.Button(
            control_frame,
            text="⏸️ Pausar",
            command=self._pausar_camara,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10,
            state=tk.DISABLED
        )
        self.btn_pausar_camara.pack(side="left", padx=5)
        
        self.btn_detener_camara = tk.Button(
            control_frame,
            text="⏹️ Detener",
            command=self._detener_camara,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10,
            state=tk.DISABLED
        )
        self.btn_detener_camara.pack(side="left", padx=5)
        
        # Botón de captura manual
        tk.Button(
            parent,
            text="📸 Captura Manual",
            command=self._captura_manual_camara,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),  # Reducido de 10 a 9
            width=15
        ).pack(pady=3)  # Reducido de 5 a 3
        
        # Configuración
        tk.Label(
            parent,
            text="⚙️ Configuración",
            bg=COLORS["background"],
            font=("Arial", 10, "bold")  # Reducido de 11 a 10
        ).pack(pady=(5, 3))  # Reducido padding
        
        config_frame = tk.Frame(parent, bg=COLORS["background"])
        config_frame.pack(fill="x", padx=10)
        
        # Sensibilidad
        tk.Label(
            config_frame,
            text="Sensibilidad:",
            bg=COLORS["background"],
            font=("Arial", 9)
        ).pack(side="left", padx=5)
        
        self.slider_sensibilidad = tk.Scale(
            config_frame,
            from_=500,
            to=5000,
            orient=tk.HORIZONTAL,
            bg=COLORS["background"],
            length=120  # Reducido de 150 a 120
        )
        self.slider_sensibilidad.set(2500)
        self.slider_sensibilidad.pack(side="left", padx=5)
        
        # Cooldown
        tk.Label(
            config_frame,
            text="Cooldown (s):",
            bg=COLORS["background"],
            font=("Arial", 9)
        ).pack(side="left", padx=5)
        
        self.slider_cooldown = tk.Scale(
            config_frame,
            from_=1,
            to=30,
            orient=tk.HORIZONTAL,
            bg=COLORS["background"],
            length=80  # Reducido de 100 a 80
        )
        self.slider_cooldown.set(5)
        self.slider_cooldown.pack(side="left", padx=5)
        
        # Historial
        tk.Label(
            parent,
            text="📜 Últimos Eventos",
            bg=COLORS["background"],
            font=("Arial", 9, "bold")  # Reducido de 10 a 9
        ).pack(pady=(5, 3))  # Reducido padding
        
        self.text_historial_camara = tk.Text(
            parent,
            font=("Consolas", 8),
            height=3,  # Reducido de 5 a 3
            wrap=tk.WORD,
            bg="#f9f9f9"
        )
        self.text_historial_camara.pack(fill="x", padx=10)
        self.text_historial_camara.config(state=tk.DISABLED)
         # === GESTIÓN DE CAPTURAS ===
        tk.Label(
            parent,
            text="📂 Capturas Guardadas",
            bg=COLORS["background"],
            font=("Arial", 10, "bold")
        ).pack(pady=(8, 3))
        
        capturas_frame = tk.Frame(parent, bg=COLORS["background"])
        capturas_frame.pack(fill="x", padx=10, pady=3)
        
        # Contador de capturas
        self.label_capturas_camara_count = tk.Label(
            capturas_frame,
            text="0 capturas",
            bg=COLORS["background"],
            font=("Arial", 9),
            fg="#666"
        )
        self.label_capturas_camara_count.pack(side="left", padx=5)
        
        # Botones de gestión
        tk.Button(
            capturas_frame,
            text="📂 Abrir Carpeta",
            command=self._abrir_carpeta_camara,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
            width=13
        ).pack(side="left", padx=2)
        
        tk.Button(
            capturas_frame,
            text="🖼️ Ver Galería",
            command=self._ver_galeria_camara,
            bg="#2196F3",
            fg="white",
            font=("Arial", 8, "bold"),
            width=13
        ).pack(side="left", padx=2)
        
        tk.Button(
            capturas_frame,
            text="🗑️ Limpiar",
            command=self._limpiar_capturas_camara,
            bg="#FF9800",
            fg="white",
            font=("Arial", 8, "bold"),
            width=10
        ).pack(side="left", padx=2)
        
        # Actualizar contador inicial
        self._actualizar_contador_capturas_camara()

        # Inicializar detector
        self.detector_camara = DetectorMovimientoCamara()
        self.detector_camara.set_callback_notificacion(self._notificar_captura_camara)
        self.actualizando_video_camara = False
        self.id_actualizacion_camara = None
        self.camara_pausada = False
        
        self._agregar_evento_camara("Sistema listo")
    
    # === MÉTODOS DE LA CÁMARA ===
    
    def _iniciar_camara(self):
        """Inicia la cámara"""
        try:
            self._agregar_evento_camara("Iniciando cámara...")
            self.detector_camara.iniciar_camara(0)
            
            # Aplicar configuración
            sensibilidad = self.slider_sensibilidad.get()
            cooldown = self.slider_cooldown.get()
            self.detector_camara.configurar_sensibilidad(sensibilidad)
            self.detector_camara.configurar_cooldown(cooldown)
            
            self._agregar_evento_camara("Iniciando detección...")
            self.detector_camara.iniciar_deteccion()
            
            # Actualizar UI
            self.btn_iniciar_camara.config(state=tk.DISABLED)
            self.btn_pausar_camara.config(state=tk.NORMAL)
            self.btn_detener_camara.config(state=tk.NORMAL)
            self.label_estado_camara.config(text="🟢 Estado: Detectando", fg="#4CAF50")
            
            # Deshabilitar configuración
            self.slider_sensibilidad.config(state=tk.DISABLED)
            self.slider_cooldown.config(state=tk.DISABLED)
            
            # Iniciar actualización de video
            self.actualizando_video_camara = True
            self.camara_pausada = False
            self._actualizar_video_camara()
            
            self._agregar_evento_camara("✅ Cámara activa")
            self._append_history("Cámara de seguridad iniciada")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar:\n{e}")
            self._agregar_evento_camara(f"❌ Error: {e}")
    
    def _pausar_camara(self):
        """Pausa/reanuda la cámara"""
        if self.camara_pausada:
            self.detector_camara.reanudar_deteccion()
            self.btn_pausar_camara.config(text="⏸️ Pausar")
            self.label_estado_camara.config(text="🟢 Estado: Detectando", fg="#4CAF50")
            self.camara_pausada = False
            self._agregar_evento_camara("Detección reanudada")
        else:
            self.detector_camara.pausar_deteccion()
            self.btn_pausar_camara.config(text="▶️ Reanudar")
            self.label_estado_camara.config(text="🟡 Estado: Pausada", fg="#FF9800")
            self.camara_pausada = True
            self._agregar_evento_camara("Detección pausada")
    
    def _detener_camara(self):
        """Detiene la cámara"""
        try:
            # Detener actualización de video
            self.actualizando_video_camara = False
            if self.id_actualizacion_camara:
                self.after_cancel(self.id_actualizacion_camara)
            
            # Detener detector
            self.detector_camara.detener_deteccion()
            self.detector_camara.detener_camara()
            
            # Limpiar canvas
            self.canvas_camara.delete("all")
            
            # Actualizar UI
            self.btn_iniciar_camara.config(state=tk.NORMAL)
            self.btn_pausar_camara.config(state=tk.DISABLED, text="⏸️ Pausar")
            self.btn_detener_camara.config(state=tk.DISABLED)
            self.label_estado_camara.config(text="⚪ Estado: Detenida", fg="#666")
            
            # Habilitar configuración
            self.slider_sensibilidad.config(state=tk.NORMAL)
            self.slider_cooldown.config(state=tk.NORMAL)
            
            self._agregar_evento_camara("Sistema detenido")
            self._append_history("Cámara de seguridad detenida")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al detener:\n{e}")
    
    def _actualizar_video_camara(self):
        """Actualiza el video de la cámara"""
        if not self.actualizando_video_camara:
            return
        
        try:
            import cv2
            from PIL import Image, ImageTk
            
            # Obtener frame
            frame = self.detector_camara.obtener_frame_actual()
            
            if frame is not None:
                # Redimensionar a tamaño compacto
                frame = cv2.resize(frame, (280, 210))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                # Actualizar canvas
                self.canvas_camara.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.canvas_camara.image = imgtk
            
            # Verificar eventos
            evento = self.detector_camara.obtener_evento()
            if evento:
                self._procesar_evento_camara(evento)
            
            # Actualizar estadísticas
            stats = self.detector_camara.obtener_estadisticas()
            self.label_movimientos.config(text=f"Movimientos: {stats['movimientos_detectados']}")
            self.label_capturas.config(text=f"Capturas: {stats['capturas_guardadas']}")
            
        except Exception as e:
            print(f"Error actualizando video: {e}")
        
        # Programar siguiente actualización
        self.id_actualizacion_camara = self.after(33, self._actualizar_video_camara)
    
    def _captura_manual_camara(self):
        """Solicita captura manual"""
        self.detector_camara.solicitar_captura_manual()
        self._agregar_evento_camara("📸 Captura manual solicitada")
    
    def _procesar_evento_camara(self, evento):
        """Procesa evento de la cámara"""
        if evento['tipo'] == 'captura_guardada':
            archivo = evento['archivo']
            tipo = evento['tipo_captura']
            
            if tipo == 'manual':
                self._agregar_evento_camara(f"📸 Captura manual: {archivo}")
                self._append_history(f"Captura manual guardada: {archivo}")
            else:
                self._agregar_evento_camara(f"🎯 Movimiento detectado: {archivo}")
                self._append_history(f"Movimiento detectado: {archivo}")
    
    def _notificar_captura_camara(self, evento):
        """Notifica captura por Telegram"""
        archivo = evento['archivo']
        tipo = evento['tipo_captura']
        timestamp = evento['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        # Buscar telegram_bot y user_manager
        telegram_bot = getattr(self, 'telegram_bot', None)
        user_manager = getattr(self, 'user_manager', None)
        
        if telegram_bot and user_manager and hasattr(user_manager, 'current_user'):
            try:
                if tipo == 'automatica':
                    mensaje = (
                        f"🎯 <b>MOVIMIENTO DETECTADO</b>\n\n"
                        f"📷 Cámara de seguridad\n"
                        f"📁 Archivo: <code>{archivo}</code>\n"
                        f"🕐 Hora: {timestamp}\n\n"
                        f"⚠️ Se ha guardado la captura"
                    )
                else:
                    mensaje = (
                        f"📸 <b>CAPTURA MANUAL</b>\n\n"
                        f"📷 Cámara de seguridad\n"
                        f"📁 Archivo: <code>{archivo}</code>\n"
                        f"🕐 Hora: {timestamp}"
                    )
                
                telegram_bot.send_message_to_user(
                    user_manager.current_user,
                    mensaje,
                    parse_mode='HTML'
                )
                
                self._agregar_evento_camara("✅ Notificación Telegram enviada")
                
            except Exception as e:
                print(f"Error Telegram: {e}")
    
    def _agregar_evento_camara(self, mensaje):
        """Agrega evento al historial"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.text_historial_camara.config(state=tk.NORMAL)
        self.text_historial_camara.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.text_historial_camara.see(tk.END)
        self.text_historial_camara.config(state=tk.DISABLED)
    def _abrir_carpeta_camara(self):
        """Abre la carpeta de capturas de cámara"""
        carpeta = "capturas_fotogramas"
        self._abrir_carpeta_sistema(carpeta)
    
    def _ver_galeria_camara(self):
        """Abre ventana de galería para cámara"""
        try:
            from views.galeria_window import GaleriaWindow
            GaleriaWindow(self, "capturas_fotogramas", "Galería - Cámara de Seguridad")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir galería:\n{e}")
    
    def _limpiar_capturas_camara(self):
        """Limpia capturas antiguas de cámara (más de 30 días)"""
        eliminadas = self._limpiar_capturas_antiguas("capturas_fotogramas", dias=30)
        messagebox.showinfo(
            "Limpieza Completada",
            f"Se eliminaron {eliminadas} capturas con más de 30 días"
        )
        self._actualizar_contador_capturas_camara()
    
    def _actualizar_contador_capturas_camara(self):
        """Actualiza el contador de capturas de cámara"""
        carpeta = Path("capturas_fotogramas")
        if carpeta.exists():
            count = len(list(carpeta.glob("*.jpg")))
            self.label_capturas_camara_count.config(text=f"{count} capturas")
        else:
            self.label_capturas_camara_count.config(text="0 capturas")
    
    # === MÉTODOS AUXILIARES COMUNES ===
    
    def _abrir_carpeta_sistema(self, carpeta):
        """Abre una carpeta en el explorador del sistema"""
        if not os.path.exists(carpeta):
            messagebox.showwarning(
                "Carpeta no existe",
                f"La carpeta '{carpeta}' no existe.\nLas capturas se crearán automáticamente al detectar."
            )
            return
        
        try:
            carpeta_abs = os.path.abspath(carpeta)
            
            if os.name == 'nt':  # Windows
                os.startfile(carpeta_abs)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', carpeta_abs])
            else:  # Linux
                subprocess.call(['xdg-open', carpeta_abs])
            
            print(f"📂 Carpeta abierta: {carpeta_abs}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{e}")
    
    def _limpiar_capturas_antiguas(self, carpeta, dias=30):
        """Elimina capturas con más de X días"""
        from datetime import datetime, timedelta
        
        carpeta_path = Path(carpeta)
        if not carpeta_path.exists():
            return 0
        
        limite = datetime.now() - timedelta(days=dias)
        eliminadas = 0
        
        try:
            for archivo in carpeta_path.glob("*.jpg"):
                fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime)
                if fecha_mod < limite:
                    archivo.unlink()
                    eliminadas += 1
                    print(f"🗑️ Eliminado: {archivo.name}")
        except Exception as e:
            print(f"❌ Error limpiando: {e}")
        
        return eliminadas
    # -----------------------
    # Utilidades (apariencia)
    # -----------------------
    def _make_circle(self, button):
        """Intenta hacer que un botón se vea más circular"""
        # Tkinter no hace verdaderos botones circulares sin canvas/imagen
        button.configure(width=3, height=1, borderwidth=2, relief="ridge")

    # -----------------------
    # Comportamiento
    # -----------------------
    def _edit_id(self):
        """Permite editar el ID del dispositivo"""
        new_id = simpledialog.askstring(
            "Editar ID", 
            "Ingrese nuevo ID:", 
            initialvalue=self.device["id"], 
            parent=self
        )
        if new_id and new_id.strip():
            self.device["id"] = new_id.strip()
            self.id_var.set(self.device["id"])
            # Refrescar vista principal en tiempo real
            self.refresh_callback()

    def _on_tipo_changed(self, new_tipo):
        """Callback cuando se cambia el tipo de dispositivo"""
        self.device["tipo"] = new_tipo
        self.refresh_callback()

    def _on_zone_changed(self, new_zone):
        """Callback cuando se cambia la zona del dispositivo"""
        # Mover dispositivo en el manager si cambió
        if new_zone != self.device["zona"]:
            self.device_manager.move_device_zone(self.device, new_zone)
            # Refrescar la vista principal para mover el widget
            self.refresh_callback()

    def _toggle_state(self):
        """Cambia el estado activo/desactivado del dispositivo"""
        self.active = not self.active
        self.device["active"] = self.active
        self._update_state_button()
        
        # Enviar comando al hardware vía serial
        tipo_dispositivo = self.device.get("tipo", "").lower()
        
        # Mapeo de tipos a nombres de comando
        mapeo_comandos = {
            # === Nombres de TU sistema (encontrados en devices.json) ===
            "sensor_de_movimiento_universal": "pir",
            "detector_laser": "laser",
            "detector_láser": "laser",
            "boton_de_panico": "panico",
            "botón_de_pánico": "panico",
            "simulador_de_presencia": "presencia",
            "alarma_silenciosa": "panico",  # Mismo hardware que pánico
            "cerradura_inteligente": None,  # Se controla desde main_menu
            
            # === Nombres originales (por compatibilidad) ===
            "sensor pir": "pir",
            "sensor de humo": "humo",
            "sensor de puerta": "puerta",
            "sensor láser": "laser",
            "sensor laser": "laser",
            "botón de pánico": "panico",
            "boton de panico": "panico",
            "simulador de presencia": "presencia",
            
            # === Variaciones comunes ===
            "sensor_de_humo": "humo",
            "detector_de_humo": "humo",
            "sensor_humo": "humo",
            "sensor_de_puerta": "puerta",
            "sensor_puerta": "puerta",
            "reed_switch": "puerta",
            "sensor_laser": "laser",
            "sensor_láser": "laser",
        }
        
        comando = mapeo_comandos.get(tipo_dispositivo)
        
        if comando:
            if self.serial_comm is None:
                mensaje = f"Error: No hay conexión serial"
            else:
                if self.active:
                    self.serial_comm.activar_dispositivo(comando)
                    mensaje = f"Estado cambiado a Activado - Comando enviado al hardware"
                else:
                    self.serial_comm.desactivar_dispositivo(comando)
                    mensaje = f"Estado cambiado a Desactivado - Comando enviado al hardware"
        else:
            mensaje = f"Estado cambiado a {'Activado' if self.active else 'Desactivado'}"
        
        # Escribir en historial
        self._append_history(mensaje)
        
        # Guardar cambios
        self.device_manager.save_devices()

    def _update_state_button(self):
        """Actualiza la apariencia del botón de estado"""
        if self.active:
            self.state_button.config(text="Activado", bg=COLORS["accent"])
        else:
            self.state_button.config(text="Desactivado", bg=COLORS["danger"])

    def _append_history(self, text):
        """Agrega un mensaje al historial del dispositivo"""
        self.hist_text.configure(state="normal")
        self.hist_text.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {text}\n")
        self.hist_text.see(tk.END)
        self.hist_text.configure(state="disabled")

    def _toggle_day(self, day):
        """Toggle para seleccionar/deseleccionar un día"""
        b = self.day_buttons[day]
        if b.cget("bg") == "lightgray":
            b.config(bg=COLORS["accent"], fg="white")
        else:
            b.config(bg="lightgray", fg="black")

    def _toggle_hour(self, h):
        """Toggle para seleccionar/deseleccionar una hora"""
        b = self.hour_buttons[h]
        if b.cget("bg") == "lightgray":
            b.config(bg=COLORS["accent"], fg="white")
        else:
            b.config(bg="lightgray", fg="black")

    def _delete_device(self):
        """Elimina el dispositivo después de confirmación"""
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este dispositivo?"):
            self.device_manager.delete_device(self.device)
            self.refresh_callback()
            self.destroy()
    
    def _abrir_cerradura(self):
        """Envía comando para abrir la cerradura"""
        if self.serial_comm.abrir_cerradura():
            self._append_history("Comando enviado: ABRIR cerradura")
            if hasattr(self, 'cerradura_estado'):
                self.cerradura_estado.config(text="Estado: Abierta", fg="#4CAF50")
        else:
            messagebox.showwarning("Error", "No se pudo enviar el comando. Verifica la conexión serial.")
    
    def _cerrar_cerradura(self):
        """Envía comando para cerrar la cerradura"""
        if self.serial_comm.cerrar_cerradura():
            self._append_history("Comando enviado: CERRAR cerradura")
            if hasattr(self, 'cerradura_estado'):
                self.cerradura_estado.config(text="Estado: Cerrada", fg="#f44336")
        else:
            messagebox.showwarning("Error", "No se pudo enviar el comando. Verifica la conexión serial.")

    def _on_close(self):
        """Cierra la ventana y actualiza la vista padre"""
        # Aseguramos actualizar la vista padre antes de cerrar
        self.refresh_callback()
        self.destroy()

    # === MÉTODOS DEL DETECTOR DE PLACAS ===
    
    def _crear_controles_detector_placas(self, parent):
        """Crea los controles para el detector de placas"""
        try:
            from controllers.detector_placas import DetectorPlacas, OCR_DISPONIBLE
        except ImportError:
            tk.Label(parent, text="❌ detector_placas.py no encontrado", bg=COLORS["background"], fg="#f44336").pack(pady=10)
            return
        
        if not OCR_DISPONIBLE:
            tk.Label(parent, text="⚠️ pytesseract no instalado", bg=COLORS["background"], fg="#FF9800", font=("Arial", 9)).pack(pady=5)
        
        tk.Label(parent, text="🚗 Control de Detector de Placas", bg=COLORS["background"], font=("Arial", 12, "bold")).pack(pady=(5, 3))  # Reducido
        
        video_frame = tk.Frame(parent, bg="black", width=280, height=210)
        video_frame.pack(pady=3)  # Reducido de 5 a 3
        video_frame.pack_propagate(False)
        
        self.canvas_placas = tk.Canvas(video_frame, width=280, height=210, bg="black")
        self.canvas_placas.pack()
        
        self.label_estado_placas = tk.Label(parent, text="⚪ Estado: Detenido", bg=COLORS["background"], font=("Arial", 9), fg="#666")  # Reducido a 9
        self.label_estado_placas.pack(pady=3)  # Reducido de 5 a 3
        
        control_frame = tk.Frame(parent, bg=COLORS["background"])
        control_frame.pack(pady=3)  # Reducido de 5 a 3
        
        self.btn_iniciar_placas = tk.Button(control_frame, text="▶️ Iniciar", command=self._iniciar_detector_placas, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=10)
        self.btn_iniciar_placas.pack(side="left", padx=5)
        
        self.btn_detener_placas = tk.Button(control_frame, text="⏹️ Detener", command=self._detener_detector_placas, bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=10, state=tk.DISABLED)
        self.btn_detener_placas.pack(side="left", padx=5)
        
        tk.Label(parent, text="📋 Placas Autorizadas", bg=COLORS["background"], font=("Arial", 10, "bold")).pack(pady=(5, 3))  # Reducido
        
        placas_list_frame = tk.Frame(parent, bg=COLORS["background"])
        placas_list_frame.pack(fill="x", padx=10)
        
        self.lista_placas_detector = tk.Listbox(placas_list_frame, font=("Courier", 9), height=3)  # Reducido de 4 a 3
        self.lista_placas_detector.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(placas_list_frame, command=self.lista_placas_detector.yview)
        scrollbar.pack(side="right", fill="y")
        self.lista_placas_detector.config(yscrollcommand=scrollbar.set)
        
        btn_placas_frame = tk.Frame(parent, bg=COLORS["background"])
        btn_placas_frame.pack(fill="x", padx=10, pady=3)  # Reducido de 5 a 3
        
        tk.Button(btn_placas_frame, text="➕ Agregar", command=self._agregar_placa, bg="#2196F3", fg="white", font=("Arial", 9), width=8).pack(side="left", padx=2)
        tk.Button(btn_placas_frame, text="➖ Eliminar", command=self._eliminar_placa, bg="#FF9800", fg="white", font=("Arial", 9), width=8).pack(side="left", padx=2)
        tk.Button(btn_placas_frame, text="🔄", command=self._actualizar_lista_placas, bg="#9C27B0", fg="white", font=("Arial", 9), width=3).pack(side="left", padx=2)
        
        tk.Label(parent, text="📜 Últimos Eventos", bg=COLORS["background"], font=("Arial", 9, "bold")).pack(pady=(5, 3))  # Reducido
        
        self.text_eventos_placas = tk.Text(parent, font=("Consolas", 8), height=3, wrap=tk.WORD, bg="#f9f9f9")  # Reducido de 4 a 3
        self.text_eventos_placas.pack(fill="x", padx=10)
        self.text_eventos_placas.config(state=tk.DISABLED)

         # === GESTIÓN DE CAPTURAS ===
        tk.Label(
            parent,
            text="📂 Capturas Guardadas",
            bg=COLORS["background"],
            font=("Arial", 10, "bold")
        ).pack(pady=(8, 3))
        
        capturas_frame = tk.Frame(parent, bg=COLORS["background"])
        capturas_frame.pack(fill="x", padx=10, pady=3)
        
        # Contador de capturas
        self.label_capturas_placas_count = tk.Label(
            capturas_frame,
            text="0 capturas",
            bg=COLORS["background"],
            font=("Arial", 9),
            fg="#666"
        )
        self.label_capturas_placas_count.pack(side="left", padx=5)
        
        # Botones de gestión
        tk.Button(
            capturas_frame,
            text="📂 Abrir Carpeta",
            command=self._abrir_carpeta_placas,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
            width=13
        ).pack(side="left", padx=2)
        
        tk.Button(
            capturas_frame,
            text="🖼️ Ver Galería",
            command=self._ver_galeria_placas,
            bg="#2196F3",
            fg="white",
            font=("Arial", 8, "bold"),
            width=13
        ).pack(side="left", padx=2)
        
        tk.Button(
            capturas_frame,
            text="🗑️ Limpiar",
            command=self._limpiar_capturas_placas,
            bg="#FF9800",
            fg="white",
            font=("Arial", 8, "bold"),
            width=10
        ).pack(side="left", padx=2)
        
        # Actualizar contador inicial
        self._actualizar_contador_capturas_placas()

        self.detector_placas = DetectorPlacas()
        self.detector_placas.set_callback_notificacion(self._notificar_placa_no_autorizada)
        self.actualizando_video_placas = False
        self.id_actualizacion_placas = None
        
        self._actualizar_lista_placas()
        self._agregar_evento_placas("Sistema listo")
    
    def _iniciar_detector_placas(self):
        """Inicia el detector"""
        try:
            from controllers.detector_placas import OCR_DISPONIBLE
            if not OCR_DISPONIBLE:
                messagebox.showerror("Error", "pytesseract no está instalado")
                return
            
            self._agregar_evento_placas("Iniciando cámara...")
            self.detector_placas.iniciar_camara(0)
            self._agregar_evento_placas("Iniciando detección...")
            self.detector_placas.iniciar_deteccion()
            
            self.btn_iniciar_placas.config(state=tk.DISABLED)
            self.btn_detener_placas.config(state=tk.NORMAL)
            self.label_estado_placas.config(text="🟢 Estado: Detectando", fg="#4CAF50")
            
            self.actualizando_video_placas = True
            self._actualizar_video_placas()
            
            self._agregar_evento_placas("✅ Sistema activo")
            self._append_history("Detector de placas iniciado")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar:\n{e}")
            self._agregar_evento_placas(f"❌ Error: {e}")
    
    def _detener_detector_placas(self):
        """Detiene el detector"""
        try:
            self.actualizando_video_placas = False
            if self.id_actualizacion_placas:
                self.after_cancel(self.id_actualizacion_placas)
            
            self.detector_placas.detener_deteccion()
            self.detector_placas.detener_camara()
            self.canvas_placas.delete("all")
            
            self.btn_iniciar_placas.config(state=tk.NORMAL)
            self.btn_detener_placas.config(state=tk.DISABLED)
            self.label_estado_placas.config(text="⚪ Estado: Detenido", fg="#666")
            
            self._agregar_evento_placas("Sistema detenido")
            self._append_history("Detector de placas detenido")
        except Exception as e:
            messagebox.showerror("Error", f"Error al detener:\n{e}")
    
    def _actualizar_video_placas(self):
        """Actualiza el video"""
        if not self.actualizando_video_placas:
            return
        
        try:
            frame = self.detector_placas.obtener_frame_actual()
            if frame is not None:
                frame = cv2.resize(frame, (280, 210))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.canvas_placas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.canvas_placas.image = imgtk
            
            evento = self.detector_placas.obtener_evento()
            if evento:
                self._procesar_evento_placa(evento)
        except Exception as e:
            print(f"Error actualizando video: {e}")
        
        self.id_actualizacion_placas = self.after(33, self._actualizar_video_placas)
    
    def _procesar_evento_placa(self, evento):
        """Procesa evento"""
        tipo = evento['tipo']
        placa = evento['placa']
        
        if tipo == 'placa_autorizada':
            self._agregar_evento_placas(f"✅ Placa OK: {placa}")
            self._append_history(f"Placa autorizada: {placa}")
        elif tipo == 'placa_no_autorizada':
            self._agregar_evento_placas(f"⚠️ NO AUTORIZADA: {placa}")
            self._append_history(f"⚠️ Placa NO autorizada: {placa}")
    
    def _notificar_placa_no_autorizada(self, evento):
        """Notifica por Telegram"""
        placa = evento['placa']
        timestamp = evento['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        telegram_bot = getattr(self, 'telegram_bot', None)
        user_manager = getattr(self, 'user_manager', None)
        
        if telegram_bot and user_manager and hasattr(user_manager, 'current_user'):
            try:
                mensaje = f"🚨 <b>ALERTA</b>\n🚗 Placa no autorizada\n📋 <code>{placa}</code>\n🕐 {timestamp}"
                telegram_bot.send_message_to_user(user_manager.current_user, mensaje, parse_mode='HTML')
                self._agregar_evento_placas("✅ Telegram enviado")
            except Exception as e:
                print(f"Error Telegram: {e}")
    
    def _agregar_placa(self):
        """Agrega placa"""
        dialogo = tk.Toplevel(self)
        dialogo.title("Agregar Placa")
        dialogo.geometry("300x140")
        dialogo.transient(self)
        dialogo.grab_set()
        
        tk.Label(dialogo, text="Placa (6 dígitos):", font=("Arial", 10)).pack(pady=10)
        entry = tk.Entry(dialogo, font=("Courier", 12, "bold"), width=8, justify=tk.CENTER)
        entry.pack(pady=5)
        entry.focus()
        
        def guardar():
            placa = entry.get().strip()
            if self.detector_placas.agregar_placa_autorizada(placa):
                messagebox.showinfo("Éxito", f"Placa {placa} agregada")
                self._actualizar_lista_placas()
                self._agregar_evento_placas(f"Agregada: {placa}")
                self._append_history(f"Placa agregada: {placa}")
                dialogo.destroy()
            else:
                messagebox.showerror("Error", "Formato inválido (6 dígitos)")
        
        btn_frame = tk.Frame(dialogo)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="✅ Guardar", command=guardar, bg="#4CAF50", fg="white", width=10).pack(side="left", padx=3)
        tk.Button(btn_frame, text="❌ Cancelar", command=dialogo.destroy, bg="#f44336", fg="white", width=10).pack(side="left", padx=3)
        entry.bind('<Return>', lambda e: guardar())
    
    def _eliminar_placa(self):
        """Elimina placa"""
        seleccion = self.lista_placas_detector.curselection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una placa")
            return
        
        placa = self.lista_placas_detector.get(seleccion[0])
        if messagebox.askyesno("Confirmar", f"¿Eliminar placa {placa}?"):
            if self.detector_placas.eliminar_placa_autorizada(placa):
                self._actualizar_lista_placas()
                self._agregar_evento_placas(f"Eliminada: {placa}")
                self._append_history(f"Placa eliminada: {placa}")
                messagebox.showinfo("Éxito", f"Placa {placa} eliminada")
    
    def _actualizar_lista_placas(self):
        """Actualiza lista"""
        self.lista_placas_detector.delete(0, tk.END)
        for placa in self.detector_placas.obtener_placas_autorizadas():
            self.lista_placas_detector.insert(tk.END, placa)
    
    def _agregar_evento_placas(self, mensaje):
        """Agrega evento"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_eventos_placas.config(state=tk.NORMAL)
        self.text_eventos_placas.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.text_eventos_placas.see(tk.END)
        self.text_eventos_placas.config(state=tk.DISABLED)
