"""
Menú principal de la aplicación con sistema de pestañas
Incluye integración con Raspberry Pi y notificaciones Telegram
"""

import tkinter as tk
from tkinter import messagebox
from config import COLORS, DEVICE_TYPES

# Importar vistas
from views.devices_frame import DevicesFrame
from views.add_device_frame import AddDeviceFrame
from views.device_detail_window import DeviceDetailWindow

# Importar controladores para Raspberry Pi y Telegram
try:
    from controllers.serial_comm import get_serial_communicator
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("⚠️ serial_comm no disponible. Conexión con Raspberry Pi deshabilitada.")

try:
    from controllers.BotMesajes import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ BotMesajes no disponible. Notificaciones Telegram deshabilitadas.")


class MainMenu(tk.Frame):
    """Frame principal con navegación por pestañas"""
    
    def __init__(self, master, device_manager, user_manager):
        super().__init__(master)
        self.master = master
        self.device_manager = device_manager
        self.user_manager = user_manager
        self.configure(bg=COLORS["background"])
        
        # Inicializar componentes de comunicación
        self.serial_comm = None
        self.telegram_bot = None
        self._init_communications()

        # Pestañas superiores
        self.tab_frame = tk.Frame(self, bg=COLORS["primary"])
        self.tab_frame.pack(fill="x")

        self.tabs = ["Dispositivos", "Historial", "Agregar", "Configuración", "Cerrar Sesión"]
        self.tab_buttons = {}
        for t in self.tabs:
            b = tk.Button(
                self.tab_frame, 
                text=t, 
                bd=0, 
                relief="flat", 
                bg=COLORS["primary"], 
                fg=COLORS["text_light"],
                command=lambda n=t: self.select_tab(n)
            )
            b.pack(side="left", padx=5, pady=5)
            self.tab_buttons[t] = b

        # Contenedor de contenido
        self.content = tk.Frame(self, bg=COLORS["background"])
        self.content.pack(fill="both", expand=True)

        # Instancias de frames
        self.frames = {}
        self.frames["Dispositivos"] = DevicesFrame(
            self.content, 
            self.device_manager, 
            self.open_device_detail
        )
        self.frames["Agregar"] = AddDeviceFrame(
            self.content, 
            self._on_device_added, 
            self.device_manager
        )
        
        # Historial de eventos
        self.frames["Historial"] = self._create_history_frame()
        
        
        # Configuración frame
        self.frames["Configuración"] = self._create_config_frame()

        # Iniciar procesamiento de mensajes del Raspberry Pi
        if SERIAL_AVAILABLE and self.serial_comm:
            self._process_device_messages()

        self.select_tab("Dispositivos")
    
    def _init_communications(self):
        """Inicializa las comunicaciones con Raspberry Pi y Telegram"""
        
        # Usar el SerialCommunicator global que ya está inicializado en app_controller
        if SERIAL_AVAILABLE:
            try:
                self.serial_comm = get_serial_communicator()
                if self.serial_comm.is_connected():
                    print(f"✅ Usando conexión serial compartida en COM5")
                else:
                    print(f"⚠️ SerialCommunicator existe pero no está conectado")
                    print(f"   Intentando conectar...")
                    # Intentar conectar si no está conectado
                    if self.serial_comm.start():
                        print(f"✅ Conexión establecida")
                    else:
                        print(f"❌ No se pudo conectar")
                        # NO poner en None, dejar el objeto por si conecta después
            except Exception as e:
                print(f"❌ Error obteniendo serial_comm: {e}")
                import traceback
                traceback.print_exc()
                self.serial_comm = None
        
        # Inicializar bot de Telegram
        if TELEGRAM_AVAILABLE:
            try:
                # TODO: Mover token a archivo de configuración
                BOT_TOKEN = "8587676832:AAHx9szhD1mjCJXzlHHN81aR90aPh3j7w-I"
                self.telegram_bot = TelegramBot(BOT_TOKEN)
                
                # Verificar bot
                bot_info = self.telegram_bot.get_me()
                if bot_info.get('ok'):
                    bot_name = bot_info['result']['first_name']
                    print(f"✅ Bot de Telegram conectado: {bot_name}")
                else:
                    print("⚠️ Error verificando bot de Telegram")
                    self.telegram_bot = None
            except Exception as e:
                print(f"❌ Error iniciando bot de Telegram: {e}")
                self.telegram_bot = None
    
    def _process_device_messages(self):
        """Procesa mensajes del Raspberry Pi periódicamente"""
        if not self.serial_comm:
            return
        
        try:
            # Obtener evento del SerialCommunicator
            mensaje = self.serial_comm.get_event()
            
            if mensaje:
                self._handle_device_event(mensaje)
                
        except Exception as e:
            print(f"Error procesando mensajes: {e}")
        
        # Llamar de nuevo en 100ms
        self.after(100, self._process_device_messages)
    
    def _handle_device_event(self, mensaje):
        """Maneja evento recibido del dispositivo Raspberry Pi"""
        print(f"📨 Mensaje recibido: {mensaje}")

        # Detectar errores del serial
        if "ERROR_SERIAL" in mensaje or mensaje.startswith("ERROR:"):
            print(f"⚠️ Error de comunicación: {mensaje}")
            return
        
        # Ignorar mensajes de sistema
        if mensaje.startswith("SYSTEM:") or mensaje.startswith("SENSORES:") or mensaje.startswith("HEARTBEAT:"):
            return
        
        # Ignorar respuestas OK (ya se procesan en otro lugar)
        if mensaje.startswith("OK:"):
            return

        # Parsear eventos (formato: "EVENT:TIPO:ESTADO" o "EVENT:TIPO")
        try:
            parts = mensaje.split(":")
            
            if len(parts) >= 2 and parts[0] == "EVENT":
                event_type = parts[1]  # PIR, HUMO, PUERTA, LASER, PANICO, SILENCIO, CERRADURA
                event_state = parts[2] if len(parts) > 2 else ""

                # Procesar según tipo de evento
                if event_type == "PIR":
                    self._handle_motion_event("Sensor PIR", event_state)
                    
                elif event_type == "HUMO":
                    self._handle_smoke_event("Detector de Humo", event_state)
                    
                elif event_type == "PANICO":
                    self._handle_alarm_event("Botón de Pánico", event_state)
                    
                elif event_type == "SILENCIO":
                    self._handle_alarm_event("Alarma Silenciosa", event_state)
                    
                elif event_type == "PUERTA":
                    self._handle_door_event(event_state)
                    
                elif event_type == "LASER":
                    self._handle_laser_event(event_state)
                    
                elif event_type == "CERRADURA":
                    self._handle_lock_event(event_state)
                    
                else:
                    print(f"Tipo de evento desconocido: {event_type}")
            else:
                print(f"Formato de mensaje no reconocido: {mensaje}")

        except Exception as e:
            print(f"Error parseando mensaje: {e}")
    
    def _handle_motion_event(self, device_id, data):
        """Maneja evento de sensor de movimiento"""
        mensaje = f"🚶 Movimiento detectado en {device_id}"
        print(mensaje)
        
        # Agregar al historial
        self._add_to_history(mensaje, "pir")
        
        # Notificación por Telegram
        if self.telegram_bot and self.user_manager.current_user:
            self.telegram_bot.send_message_to_user(
                self.user_manager.current_user,
                f"🔔 <b>Sensor de Movimiento</b>\n\n{mensaje}",
                parse_mode='HTML'
            )
        
        # Mostrar alerta visual
        messagebox.showinfo("Sensor de Movimiento", mensaje)
    
    def _handle_alarm_event(self, device_id, data):
        """Maneja evento de alarma"""
        mensaje = f"🚨 ALARMA activada en {device_id}"
        print(mensaje)
        
        # Agregar al historial
        self._add_to_history(mensaje, "panico")
        
        # Notificación urgente por Telegram
        if self.telegram_bot and self.user_manager.current_user:
            self.telegram_bot.send_message_to_user(
                self.user_manager.current_user,
                f"🚨 <b>¡ALERTA DE SEGURIDAD!</b>\n\n{mensaje}\n\nDispositivo: {device_id}\nDatos: {data}",
                parse_mode='HTML'
            )
        
        # Mostrar mensaje en la aplicación
        messagebox.showwarning("Alerta de Seguridad", mensaje)
    
    def _handle_smoke_event(self, device_id, data):
        """Maneja evento de detector de humo"""
        mensaje = f"💨 Humo detectado en {device_id}"
        print(mensaje)
        
        # Agregar al historial
        self._add_to_history(mensaje, "humo")
        
        # Notificación por Telegram
        if self.telegram_bot and self.user_manager.current_user:
            self.telegram_bot.send_message_to_user(
                self.user_manager.current_user,
                f"⚠️ <b>Detector de Humo</b>\n\n{mensaje}",
                parse_mode='HTML'
            )
        
        # Mostrar alerta visual
        messagebox.showwarning("Detector de Humo", mensaje)
    
    def _handle_status_update(self, device_id, data):
        """Maneja actualización de estado de dispositivo"""
        print(f"📊 Actualización de estado: {device_id} - {data}")
        # Actualizar estado en device_manager si es necesario
    
    def _handle_door_event(self, state):
        """Maneja evento de puerta/ventana"""
        if state == "ABIERTA":
            mensaje = "🚪 Puerta/Ventana ABIERTA"
            print(mensaje)
            
            # Agregar al historial
            self._add_to_history(mensaje, "puerta")
            
            if self.telegram_bot and self.user_manager.current_user:
                self.telegram_bot.send_message_to_user(
                    self.user_manager.current_user,
                    f"🚪 <b>Alerta de Acceso</b>\n\n{mensaje}",
                    parse_mode='HTML'
                )
            messagebox.showwarning("Alerta de Acceso", mensaje)
        elif state == "CERRADA":
            mensaje = "🚪 Puerta/Ventana cerrada"
            print(mensaje)
            self._add_to_history(mensaje, "puerta")
    
    def _handle_laser_event(self, state):
        """Maneja evento de láser"""
        if state == "INTERRUMPIDO":
            mensaje = "🔴 Perímetro láser INTERRUMPIDO"
            print(mensaje)
            
            # Agregar al historial
            self._add_to_history(mensaje, "laser")
            
            if self.telegram_bot and self.user_manager.current_user:
                self.telegram_bot.send_message_to_user(
                    self.user_manager.current_user,
                    f"🔴 <b>Alerta de Seguridad</b>\n\n{mensaje}",
                    parse_mode='HTML'
                )
            messagebox.showwarning("Alerta de Seguridad", mensaje)
        elif state == "OK":
            mensaje = "🟢 Perímetro láser OK"
            print(mensaje)
            self._add_to_history(mensaje, "laser")
    
    def _handle_lock_event(self, state):
        """Maneja evento de cerradura"""
        estados = {
            "ABRIENDO": "🔓 Abriendo cerradura...",
            "ABIERTA": "🔓 Cerradura ABIERTA",
            "CERRANDO": "🔒 Cerrando cerradura...",
            "CERRADA": "🔒 Cerradura CERRADA",
            "YA_ABIERTA": "🔓 Cerradura ya estaba abierta",
            "YA_CERRADA": "🔒 Cerradura ya estaba cerrada"
        }
        mensaje = estados.get(state, f"Cerradura: {state}")
        print(mensaje)
        
        # Agregar al historial
        self._add_to_history(mensaje, "cerradura")
    
    def _create_history_frame(self):
        """Crea el frame de historial de eventos"""
        from tkinter import scrolledtext
        from datetime import datetime
        
        history_frame = tk.Frame(self.content, bg=COLORS["background"])
        
        # Título
        tk.Label(
            history_frame,
            text="📋 Historial de Eventos",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 16, "bold")
        ).pack(pady=20)
        
        # Botones de control
        button_frame = tk.Frame(history_frame, bg=COLORS["background"])
        button_frame.pack(pady=10)
        
        tk.Button(
            button_frame,
            text="🗑️ Limpiar Historial",
            bg=COLORS["danger"],
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=15,
            pady=5,
            command=self._clear_history
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="💾 Exportar",
            bg=COLORS["accent"],
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=15,
            pady=5,
            command=self._export_history
        ).pack(side="left", padx=5)
        
        # Área de texto con scroll
        self.history_text = scrolledtext.ScrolledText(
            history_frame,
            width=80,
            height=20,
            bg="#ffffff",
            fg=COLORS["text_dark"],
            font=("Consolas", 10),
            wrap=tk.WORD,
            relief="solid",
            borderwidth=1
        )
        self.history_text.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Configurar tags para colores
        self.history_text.tag_config("timestamp", foreground="#666666")
        self.history_text.tag_config("pir", foreground="#2196F3")
        self.history_text.tag_config("humo", foreground="#FF5722")
        self.history_text.tag_config("panico", foreground="#F44336")
        self.history_text.tag_config("puerta", foreground="#FF9800")
        self.history_text.tag_config("laser", foreground="#9C27B0")
        self.history_text.tag_config("cerradura", foreground="#4CAF50")
        self.history_text.tag_config("sistema", foreground="#00BCD4")
        
        # Deshabilitar edición
        self.history_text.config(state="disabled")
        
        # Agregar mensaje inicial
        self._add_to_history("Sistema iniciado", "sistema")
        
        return history_frame
    
    def _add_to_history(self, mensaje, tipo="sistema"):
        """Agrega un mensaje al historial"""
        from datetime import datetime
        
        if not hasattr(self, 'history_text'):
            return
        
        # Obtener timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Habilitar edición temporalmente
        self.history_text.config(state="normal")
        
        # Agregar timestamp
        self.history_text.insert("end", f"[{timestamp}] ", "timestamp")
        
        # Agregar mensaje con color según tipo
        self.history_text.insert("end", f"{mensaje}\n", tipo)
        
        # Auto-scroll al final
        self.history_text.see("end")
        
        # Deshabilitar edición
        self.history_text.config(state="disabled")
    
    def _clear_history(self):
        """Limpia el historial"""
        if messagebox.askyesno("Confirmar", "¿Deseas limpiar todo el historial?"):
            self.history_text.config(state="normal")
            self.history_text.delete("1.0", "end")
            self.history_text.config(state="disabled")
            self._add_to_history("Historial limpiado", "sistema")
    
    def _export_history(self):
        """Exporta el historial a un archivo"""
        from tkinter import filedialog
        from datetime import datetime
        
        # Pedir ubicación del archivo
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")],
            initialfile=f"historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    content = self.history_text.get("1.0", "end")
                    f.write(content)
                messagebox.showinfo("Éxito", f"Historial exportado a:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar el historial:\n{e}")
    
    def _create_config_frame(self):
        """Crea el frame de configuración"""
        config_frame = tk.Frame(self.content, bg=COLORS["background"])

        tk.Label(
            config_frame,
            text="Configuración",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 16, "bold")
        ).pack(pady=20)

        # Información del usuario
        if self.user_manager.current_user:
            if profile := self.user_manager.get_current_user_profile():
                info_frame = tk.Frame(config_frame, bg=COLORS["background"])
                info_frame.pack(pady=10, padx=20, fill="x")

                tk.Label(
                    info_frame,
                    text=f"Usuario: {profile.get('email', 'N/A')}",
                    bg=COLORS["background"],
                    fg=COLORS["text_dark"],
                    font=("Arial", 11)
                ).pack(anchor="w", pady=5)

                tk.Label(
                    info_frame,
                    text=f"Telegram: {profile.get('telegram', 'No configurado')}",
                    bg=COLORS["background"],
                    fg=COLORS["text_dark"],
                    font=("Arial", 11)
                ).pack(anchor="w", pady=5)

        # Estado de conexiones
        status_frame = tk.LabelFrame(
            config_frame,
            text="Estado de Conexiones",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 12, "bold"),
            padx=10,
            pady=10
        )
        status_frame.pack(pady=20, padx=20, fill="x")

        # Estado Raspberry Pi
        serial_status = "✅ Conectado" if (SERIAL_AVAILABLE and self.serial_comm) else "❌ Desconectado"
        tk.Label(
            status_frame,
            text=f"Raspberry Pi: {serial_status}",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=3)

        # Estado Telegram
        telegram_status = "✅ Conectado" if (TELEGRAM_AVAILABLE and self.telegram_bot) else "❌ Desconectado"
        tk.Label(
            status_frame,
            text=f"Bot Telegram: {telegram_status}",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=3)

        # Botón para vincular Telegram
        if TELEGRAM_AVAILABLE and self.telegram_bot:
            tk.Button(
                config_frame,
                text="Vincular cuenta de Telegram",
                bg=COLORS["secondary"],
                fg=COLORS["text_light"],
                font=("Arial", 10, "bold"),
                command=self._vincular_telegram
            ).pack(pady=10)

        return config_frame
    
    def _vincular_telegram(self):
        """Vincula la cuenta del usuario con Telegram"""
        if not self.telegram_bot:
            messagebox.showerror("Error", "Bot de Telegram no disponible")
            return
        
        # Obtener actualizaciones del bot
        self.telegram_bot.get_updates()
        
        # Verificar si el usuario ya está vinculado
        email = self.user_manager.current_user
        chat_id = self.telegram_bot.get_user_chat_id(email)
        
        if chat_id:
            messagebox.showinfo(
                "Vinculación exitosa",
                f"Tu cuenta ya está vinculada con Telegram.\nChat ID: {chat_id}"
            )
        else:
            messagebox.showinfo(
                "Instrucciones",
                "Para vincular tu cuenta:\n\n"
                "1. Abre Telegram\n"
                "2. Busca el bot y envíale un mensaje\n"
                "3. Vuelve a presionar este botón\n\n"
                "El sistema detectará automáticamente tu cuenta."
            )

    def select_tab(self, name):
        """Cambia la pestaña activa"""
        # Actualizar apariencia de botones
        for tn, btn in self.tab_buttons.items():
            if tn == name:
                btn.configure(
                    bg=COLORS["secondary"], 
                    fg=COLORS["text_light"], 
                    font=("Arial", 10, "bold")
                )
            else:
                btn.configure(
                    bg=COLORS["primary"], 
                    fg=COLORS["accent"], 
                    font=("Arial", 9)
                )

        # Ocultar todos los frames
        for child in self.content.winfo_children():
            child.pack_forget()

        # Manejar caso especial de cerrar sesión
        if name == "Cerrar Sesión":
            # Ya no necesitamos detener el serial_comm aquí
            # porque es un singleton global que se mantiene activo
            # y se cierra solo cuando se cierra la aplicación completa
            
            # Hacer logout y volver a login
            self.user_manager.logout()
            self.master.show_login()
            return
            
        # Mostrar el frame seleccionado
        frame = self.frames[name]
        frame.pack(fill="both", expand=True)
        
        # Cuando mostramos dispositivos, refrescar contenido
        if name == "Dispositivos":
            frame.refresh()

    def _on_device_added(self, device):
        """Callback después de agregar un dispositivo"""
        # Luego de agregar, mostrar pestaña Dispositivos y refrescar
        self.select_tab("Dispositivos")

    def open_device_detail(self, device):
        """Abre la ventana de detalle para un dispositivo"""
        DeviceDetailWindow(
            self.master, 
            device, 
            self.device_manager, 
            self._refresh_devices, 
            DEVICE_TYPES
        )

    def _refresh_devices(self):
        """Refresca el frame de dispositivos"""
        f = self.frames.get("Dispositivos")
        if f:
            f.refresh()
    
    def destroy(self):
        """Limpieza al destruir el widget"""
        # El serial_comm es un singleton global
        # No lo cerramos aquí porque puede estar siendo usado por otras partes
        # Se cierra automáticamente en app_controller cuando se cierra la app
        
        super().destroy()
