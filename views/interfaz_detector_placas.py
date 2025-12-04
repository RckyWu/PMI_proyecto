"""
Interfaz Gráfica para Detector de Placas
Integración con Telegram para notificaciones
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import cv2
from PIL import Image, ImageTk
import threading
from datetime import datetime
from detector_placas import DetectorPlacas, OCR_DISPONIBLE

# Importar Telegram si está disponible
try:
    from controllers.BotMesajes import TelegramBot
    TELEGRAM_DISPONIBLE = True
except ImportError:
    TELEGRAM_DISPONIBLE = False
    print("⚠️ BotMesajes no disponible - notificaciones Telegram deshabilitadas")


class InterfazDetectorPlacas:
    """Interfaz gráfica para el detector de placas"""
    
    def __init__(self, root, user_manager=None, telegram_bot=None):
        self.root = root
        self.root.title("🚗 Detector de Placas - Costa Rica")
        self.root.geometry("1200x800")
        
        # Detector de placas
        self.detector = DetectorPlacas()
        self.detector.set_callback_notificacion(self.notificar_placa_no_autorizada)
        
        # User manager y Telegram
        self.user_manager = user_manager
        self.telegram_bot = telegram_bot
        
        # Control de actualización de video
        self.actualizando_video = False
        self.id_actualizacion = None
        
        # Crear interfaz
        self._crear_interfaz()
        
        # Verificar OCR
        if not OCR_DISPONIBLE:
            messagebox.showwarning(
                "OCR No Disponible",
                "pytesseract no está instalado.\n\n"
                "Para usar el reconocimiento de placas:\n"
                "1. pip install pytesseract\n"
                "2. Instalar Tesseract OCR desde:\n"
                "   https://github.com/UB-Mannheim/tesseract/wiki"
            )
        
        # Configurar cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
    
    def _crear_interfaz(self):
        """Crea la interfaz gráfica"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === PANEL IZQUIERDO: VIDEO ===
        left_frame = tk.Frame(main_frame, bg="#f0f0f0")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Título
        tk.Label(
            left_frame,
            text="🎥 Vista de Cámara",
            font=("Arial", 14, "bold"),
            bg="#f0f0f0"
        ).pack(pady=5)
        
        # Canvas para video
        self.canvas_video = tk.Canvas(left_frame, width=640, height=480, bg="black")
        self.canvas_video.pack(pady=5)
        
        # Estado
        self.label_estado = tk.Label(
            left_frame,
            text="⚪ Estado: Detenido",
            font=("Arial", 11),
            bg="#f0f0f0",
            fg="#666"
        )
        self.label_estado.pack(pady=5)
        
        # Controles
        control_frame = tk.Frame(left_frame, bg="#f0f0f0")
        control_frame.pack(pady=10)
        
        self.btn_iniciar = tk.Button(
            control_frame,
            text="▶️ Iniciar Detección",
            command=self.iniciar_deteccion,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            width=18,
            height=2
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)
        
        self.btn_detener = tk.Button(
            control_frame,
            text="⏹️ Detener",
            command=self.detener_deteccion,
            bg="#f44336",
            fg="white",
            font=("Arial", 11, "bold"),
            width=18,
            height=2,
            state=tk.DISABLED
        )
        self.btn_detener.pack(side=tk.LEFT, padx=5)
        
        # === PANEL DERECHO: PLACAS Y EVENTOS ===
        right_frame = tk.Frame(main_frame, bg="#f0f0f0")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # --- PLACAS AUTORIZADAS ---
        placas_frame = tk.LabelFrame(
            right_frame,
            text="📋 Placas Autorizadas",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
            padx=10,
            pady=10
        )
        placas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Lista de placas
        self.lista_placas = tk.Listbox(
            placas_frame,
            font=("Courier", 11),
            height=8
        )
        self.lista_placas.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scroll para lista
        scrollbar_placas = tk.Scrollbar(placas_frame, command=self.lista_placas.yview)
        self.lista_placas.config(yscrollcommand=scrollbar_placas.set)
        
        # Botones de gestión
        btn_placas_frame = tk.Frame(placas_frame, bg="#f0f0f0")
        btn_placas_frame.pack(fill=tk.X)
        
        tk.Button(
            btn_placas_frame,
            text="➕ Agregar",
            command=self.agregar_placa,
            bg="#2196F3",
            fg="white",
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_placas_frame,
            text="➖ Eliminar",
            command=self.eliminar_placa,
            bg="#FF9800",
            fg="white",
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_placas_frame,
            text="🔄 Actualizar",
            command=self.actualizar_lista_placas,
            bg="#9C27B0",
            fg="white",
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        # --- EVENTOS / HISTORIAL ---
        eventos_frame = tk.LabelFrame(
            right_frame,
            text="📜 Eventos Recientes",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
            padx=10,
            pady=10
        )
        eventos_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_eventos = scrolledtext.ScrolledText(
            eventos_frame,
            font=("Consolas", 9),
            height=15,
            wrap=tk.WORD
        )
        self.text_eventos.pack(fill=tk.BOTH, expand=True)
        self.text_eventos.config(state=tk.DISABLED)
        
        # Configurar tags para colores
        self.text_eventos.tag_config("autorizada", foreground="#4CAF50")
        self.text_eventos.tag_config("no_autorizada", foreground="#f44336")
        self.text_eventos.tag_config("sistema", foreground="#2196F3")
        
        # Cargar placas iniciales
        self.actualizar_lista_placas()
        self.agregar_evento_sistema("Sistema iniciado")
    
    def iniciar_deteccion(self):
        """Inicia la detección de placas"""
        try:
            # Verificar OCR
            if not OCR_DISPONIBLE:
                messagebox.showerror(
                    "Error",
                    "pytesseract no está instalado.\n"
                    "El reconocimiento de placas no funcionará."
                )
                return
            
            # Iniciar cámara
            self.agregar_evento_sistema("Iniciando cámara...")
            self.detector.iniciar_camara(0)
            
            # Iniciar detección
            self.agregar_evento_sistema("Iniciando detección de movimiento...")
            self.detector.iniciar_deteccion()
            
            # Actualizar UI
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_detener.config(state=tk.NORMAL)
            self.label_estado.config(text="🟢 Estado: Detectando", fg="#4CAF50")
            
            # Iniciar actualización de video
            self.actualizando_video = True
            self.actualizar_video()
            
            self.agregar_evento_sistema("✅ Sistema activo - Detectando placas...")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar la cámara:\n{e}")
            self.agregar_evento_sistema(f"❌ Error: {e}")
    
    def detener_deteccion(self):
        """Detiene la detección"""
        try:
            # Detener actualización de video
            self.actualizando_video = False
            if self.id_actualizacion:
                self.root.after_cancel(self.id_actualizacion)
            
            # Detener detector
            self.detector.detener_deteccion()
            self.detector.detener_camara()
            
            # Limpiar canvas
            self.canvas_video.delete("all")
            
            # Actualizar UI
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_detener.config(state=tk.DISABLED)
            self.label_estado.config(text="⚪ Estado: Detenido", fg="#666")
            
            self.agregar_evento_sistema("Sistema detenido")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al detener:\n{e}")
    
    def actualizar_video(self):
        """Actualiza el frame del video en el canvas"""
        if not self.actualizando_video:
            return
        
        try:
            # Obtener frame actual
            frame = self.detector.obtener_frame_actual()
            
            if frame is not None:
                # Redimensionar para el canvas
                frame = cv2.resize(frame, (640, 480))
                
                # Convertir BGR a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convertir a ImageTk
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                # Actualizar canvas
                self.canvas_video.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.canvas_video.image = imgtk  # Mantener referencia
            
            # Verificar eventos
            evento = self.detector.obtener_evento()
            if evento:
                self.procesar_evento(evento)
            
        except Exception as e:
            print(f"Error actualizando video: {e}")
        
        # Programar siguiente actualización
        self.id_actualizacion = self.root.after(33, self.actualizar_video)  # ~30 FPS
    
    def procesar_evento(self, evento):
        """Procesa un evento del detector"""
        tipo = evento['tipo']
        placa = evento['placa']
        timestamp = evento['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        if tipo == 'placa_autorizada':
            self.agregar_evento_autorizada(f"[{timestamp}] Placa autorizada: {placa}")
        elif tipo == 'placa_no_autorizada':
            self.agregar_evento_no_autorizada(f"[{timestamp}] ⚠️ PLACA NO AUTORIZADA: {placa}")
    
    def notificar_placa_no_autorizada(self, evento):
        """Callback para notificaciones de placas no autorizadas"""
        placa = evento['placa']
        timestamp = evento['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        # Notificar por Telegram si está disponible
        if TELEGRAM_DISPONIBLE and self.telegram_bot and self.user_manager:
            try:
                mensaje = (
                    f"🚨 <b>ALERTA DE SEGURIDAD</b>\n\n"
                    f"🚗 Vehículo no autorizado detectado\n"
                    f"📋 Placa: <code>{placa}</code>\n"
                    f"🕐 Hora: {timestamp}\n\n"
                    f"⚠️ Esta placa no está en la lista de autorizados"
                )
                
                self.telegram_bot.send_message_to_user(
                    self.user_manager.current_user,
                    mensaje,
                    parse_mode='HTML'
                )
                
                self.agregar_evento_sistema(f"✅ Notificación enviada por Telegram")
                
            except Exception as e:
                print(f"Error enviando notificación Telegram: {e}")
                self.agregar_evento_sistema(f"⚠️ Error en notificación Telegram")
    
    def agregar_placa(self):
        """Muestra diálogo para agregar placa"""
        dialogo = tk.Toplevel(self.root)
        dialogo.title("Agregar Placa Autorizada")
        dialogo.geometry("350x150")
        dialogo.transient(self.root)
        dialogo.grab_set()
        
        tk.Label(
            dialogo,
            text="Ingrese la placa (6 dígitos):",
            font=("Arial", 11)
        ).pack(pady=20)
        
        entry = tk.Entry(dialogo, font=("Courier", 14, "bold"), width=10, justify=tk.CENTER)
        entry.pack(pady=10)
        entry.focus()
        
        def guardar():
            placa = entry.get().strip()
            if self.detector.agregar_placa_autorizada(placa):
                messagebox.showinfo("Éxito", f"Placa {placa} agregada")
                self.actualizar_lista_placas()
                self.agregar_evento_sistema(f"Placa agregada: {placa}")
                dialogo.destroy()
            else:
                messagebox.showerror("Error", "Formato inválido.\nDebe ser 6 dígitos (000000-999999)")
        
        btn_frame = tk.Frame(dialogo)
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="✅ Guardar",
            command=guardar,
            bg="#4CAF50",
            fg="white",
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="❌ Cancelar",
            command=dialogo.destroy,
            bg="#f44336",
            fg="white",
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        entry.bind('<Return>', lambda e: guardar())
    
    def eliminar_placa(self):
        """Elimina la placa seleccionada"""
        seleccion = self.lista_placas.curselection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una placa para eliminar")
            return
        
        placa = self.lista_placas.get(seleccion[0])
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar la placa {placa}?"):
            if self.detector.eliminar_placa_autorizada(placa):
                self.actualizar_lista_placas()
                self.agregar_evento_sistema(f"Placa eliminada: {placa}")
                messagebox.showinfo("Éxito", f"Placa {placa} eliminada")
    
    def actualizar_lista_placas(self):
        """Actualiza la lista de placas autorizadas"""
        self.lista_placas.delete(0, tk.END)
        for placa in self.detector.obtener_placas_autorizadas():
            self.lista_placas.insert(tk.END, placa)
    
    def agregar_evento_autorizada(self, mensaje):
        """Agrega evento de placa autorizada al historial"""
        self.text_eventos.config(state=tk.NORMAL)
        self.text_eventos.insert(tk.END, mensaje + "\n", "autorizada")
        self.text_eventos.see(tk.END)
        self.text_eventos.config(state=tk.DISABLED)
    
    def agregar_evento_no_autorizada(self, mensaje):
        """Agrega evento de placa no autorizada al historial"""
        self.text_eventos.config(state=tk.NORMAL)
        self.text_eventos.insert(tk.END, mensaje + "\n", "no_autorizada")
        self.text_eventos.see(tk.END)
        self.text_eventos.config(state=tk.DISABLED)
    
    def agregar_evento_sistema(self, mensaje):
        """Agrega evento del sistema al historial"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.text_eventos.config(state=tk.NORMAL)
        self.text_eventos.insert(tk.END, f"[{timestamp}] {mensaje}\n", "sistema")
        self.text_eventos.see(tk.END)
        self.text_eventos.config(state=tk.DISABLED)
    
    def cerrar_ventana(self):
        """Maneja el cierre de la ventana"""
        if self.actualizando_video:
            self.detener_deteccion()
        self.root.destroy()


# Función para iniciar la interfaz de forma independiente
def iniciar_interfaz_placas():
    """Inicia la interfaz de placas de forma independiente"""
    root = tk.Tk()
    app = InterfazDetectorPlacas(root)
    root.mainloop()


if __name__ == "__main__":
    iniciar_interfaz_placas()
