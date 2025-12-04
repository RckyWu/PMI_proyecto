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
        
        # Historial placeholder
        self.frames["Historial"] = tk.Frame(self.content, bg=COLORS["background"])
        tk.Label(
            self.frames["Historial"], 
            text="Historial general", 
            bg=COLORS["background"],
            font=("Arial", 14, "bold")
        ).pack(pady=20)
        
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
                    print(f"⚠️ SerialCommunicator no está conectado")
                    self.serial_comm = None
            except Exception as e:
                print(f"❌ Error obteniendo serial_comm: {e}")
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
        self._extracted_from__handle_smoke_event_3(
            '🚶 Movimiento detectado en ',
            device_id,
            '🔔 <b>Sensor de Movimiento</b>\n\n',
        )
    
    def _handle_alarm_event(self, device_id, data):
        """Maneja evento de alarma"""
        mensaje = f"🚨 ALARMA activada en {device_id}"
        print(mensaje)
        
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
        self._extracted_from__handle_smoke_event_3(
            '💨 Humo detectado en ', device_id, '⚠️ <b>Detector de Humo</b>\n\n'
        )

    # TODO Rename this here and in `_handle_motion_event` and `_handle_smoke_event`
    def _extracted_from__handle_smoke_event_3(self, arg0, device_id, arg2):
        mensaje = f"{arg0}{device_id}"
        print(mensaje)
        if self.telegram_bot and self.user_manager.current_user:
            self.telegram_bot.send_message_to_user(
                self.user_manager.current_user,
                f"{arg2}{mensaje}\n\nDispositivo: {device_id}",
                parse_mode='HTML',
            )
    
    def _handle_status_update(self, device_id, data):
        """Maneja actualización de estado de dispositivo"""
        print(f"📊 Actualización de estado: {device_id} - {data}")
        # Actualizar estado en device_manager si es necesario
    
    def _handle_door_event(self, state):
        """Maneja evento de puerta/ventana"""
        if state == "ABIERTA":
            mensaje = "🚪 Puerta/Ventana ABIERTA"
            print(mensaje)
            if self.telegram_bot and self.user_manager.current_user:
                self.telegram_bot.send_message_to_user(
                    self.user_manager.current_user,
                    f"🚪 <b>Alerta de Acceso</b>\n\n{mensaje}",
                    parse_mode='HTML'
                )
            messagebox.showwarning("Alerta de Acceso", mensaje)
        elif state == "CERRADA":
            print("🚪 Puerta/Ventana cerrada")
    
    def _handle_laser_event(self, state):
        """Maneja evento de láser"""
        if state == "INTERRUMPIDO":
            mensaje = "🔴 Perímetro láser INTERRUMPIDO"
            print(mensaje)
            if self.telegram_bot and self.user_manager.current_user:
                self.telegram_bot.send_message_to_user(
                    self.user_manager.current_user,
                    f"🔴 <b>Alerta de Seguridad</b>\n\n{mensaje}",
                    parse_mode='HTML'
                )
            messagebox.showwarning("Alerta de Seguridad", mensaje)
        elif state == "OK":
            print("🟢 Perímetro láser OK")
    
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
