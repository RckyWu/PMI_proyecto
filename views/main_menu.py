"""
Menu principal de la aplicacion con sistema de pestañas
Incluye integracion con Raspberry Pi y notificaciones Telegram
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
from config import COLORS, DEVICE_TYPES

from views.devices_frame import DevicesFrame
from views.add_device_frame import AddDeviceFrame
from views.device_detail_window import DeviceDetailWindow
from views.telegram_link_frame import TelegramLinkFrame

# Importaciones condicionales
try:
    from controllers.device_listener import DeviceListener

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("device_listener no disponible. Conexion con Raspberry Pi deshabilitada.")

try:
    from controllers.BotMesajes import TelegramBot
    from controllers.event_handler import DeviceEventHandler

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("TelegramBot no disponible. Notificaciones Telegram deshabilitadas.")


class MainMenu(tk.Frame):
    def __init__(self, master, device_manager, user_manager):
        super().__init__(master)
        self.master = master
        self.device_manager = device_manager
        self.user_manager = user_manager
        self.configure(bg=COLORS["background"])

        self.device_listener = None
        self.telegram_bot = None
        self.event_handler = None

        self._init_communications()

        # Interfaz de pestañas
        self.tab_frame = tk.Frame(self, bg=COLORS["primary"])
        self.tab_frame.pack(fill="x")

        self.tabs = ["Dispositivos", "Historial", "Agregar", "Configuracion", "Telegram", "Cerrar Sesion"]
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

        self.content = tk.Frame(self, bg=COLORS["background"])
        self.content.pack(fill="both", expand=True)

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

        self.frames["Historial"] = tk.Frame(self.content, bg=COLORS["background"])
        tk.Label(
            self.frames["Historial"],
            text="Historial general",
            bg=COLORS["background"],
            font=("Arial", 14, "bold")
        ).pack(pady=20)

        self.frames["Configuracion"] = self._create_config_frame()

        # Frame de Telegram - inicializar solo si el bot está disponible
        if TELEGRAM_AVAILABLE:
            self.frames["Telegram"] = TelegramLinkFrame(
                self.content,
                self.user_manager,
                self.telegram_bot
            )
        else:
            self.frames["Telegram"] = tk.Frame(self.content, bg=COLORS["background"])
            tk.Label(
                self.frames["Telegram"],
                text="Bot de Telegram no disponible",
                bg=COLORS["background"],
                fg=COLORS["danger"],
                font=("Arial", 14, "bold")
            ).pack(pady=50)

        # Iniciar procesamiento de eventos del hardware
        if SERIAL_AVAILABLE and self.device_listener:
            self._start_event_processing()

        self.select_tab("Dispositivos")

    def _init_communications(self):
        """Inicializa todas las comunicaciones"""
        # 1. Inicializar comunicación serial con hardware
        if SERIAL_AVAILABLE:
            try:
                puerto = "COM5"
                self.device_listener = DeviceListener(puerto=puerto, baud=115200)
                self.device_listener.start()
                print(f"Conexion serial iniciada en {puerto}")
            except Exception as e:
                print(f"Error iniciando conexion serial: {e}")
                self.device_listener = None

        # 2. Inicializar bot de Telegram
        if TELEGRAM_AVAILABLE:
            try:
                BOT_TOKEN = "8587676832:AAHx9szhD1mjCJXzlHHN81aR90aPh3j7w-I"
                self.telegram_bot = TelegramBot(BOT_TOKEN)

                # CRÍTICO: Pasar el user_manager al bot
                self.telegram_bot.user_manager = self.user_manager

                print(f"Bot de Telegram inicializado")
                print(f"Usuario actual: {self.user_manager.current_user}")

            except Exception as e:
                print(f"Error iniciando bot de Telegram: {e}")
                self.telegram_bot = None

        # 3. Crear manejador de eventos (SOLO si hay bot)
        if self.telegram_bot:
            self.event_handler = DeviceEventHandler(
                self.user_manager,
                self.telegram_bot
            )
            print("Manejador de eventos creado")

    def _start_event_processing(self):
        """Inicia el procesamiento de eventos del hardware"""
        if not self.device_listener:
            return

        self._process_device_messages()
        print("Procesamiento de eventos iniciado")

    def _process_device_messages(self):
        """Procesa los mensajes recibidos del hardware"""
        if not self.device_listener:
            return

        try:
            # Procesar todos los mensajes en la cola
            while not self.device_listener.queue.empty():
                mensaje = self.device_listener.queue.get_nowait()
                self._handle_raw_message(mensaje)
        except Exception as e:
            print(f"Error procesando mensajes: {e}")

        # Programar siguiente verificación en 100ms
        self.after(100, self._process_device_messages)

    def _handle_raw_message(self, mensaje):
        """Procesa un mensaje crudo del hardware"""
        if "ERROR_SERIAL" in mensaje:
            print("Error de comunicacion serial")
            return

        try:
            # Parsear formato: DISPOSITIVO:EVENTO:ZONA:DATOS_ADICIONALES
            parts = mensaje.split(":")

            if len(parts) >= 2:
                hardware_id = parts[0].strip().upper()
                event_type = parts[1].strip().upper()
                zone = parts[2].strip() if len(parts) > 2 else "Desconocida"
                data = ":".join(parts[3:]).strip() if len(parts) > 3 else ""

                # Log del evento en consola
                print(f"Evento recibido: {hardware_id} | {event_type} | {zone}")

                # Procesar evento si hay manejador configurado
                if self.event_handler:
                    self.event_handler.handle_event(hardware_id, event_type, zone, data)
                else:
                    print(f"Manejador de eventos no disponible")

            else:
                print(f"Formato de mensaje invalido: {mensaje}")

        except Exception as e:
            print(f"Error parseando mensaje: {e}")

    def _create_config_frame(self):
        config_frame = tk.Frame(self.content, bg=COLORS["background"])

        tk.Label(
            config_frame,
            text="Configuracion",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 16, "bold")
        ).pack(pady=20)

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

                if profile.get('chat_id'):
                    tk.Label(
                        info_frame,
                        text=f"Chat ID: {profile.get('chat_id')}",
                        bg=COLORS["background"],
                        fg=COLORS["text_dark"],
                        font=("Arial", 11)
                    ).pack(anchor="w", pady=5)

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

        serial_status = "Conectado" if (SERIAL_AVAILABLE and self.device_listener) else "Desconectado"
        tk.Label(
            status_frame,
            text=f"Raspberry Pi: {serial_status}",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=3)

        telegram_status = "Conectado" if (TELEGRAM_AVAILABLE and self.telegram_bot) else "Desconectado"
        tk.Label(
            status_frame,
            text=f"Bot Telegram: {telegram_status}",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=3)

        return config_frame

    def select_tab(self, name):
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

        for child in self.content.winfo_children():
            child.pack_forget()

        if name == "Cerrar Sesion":
            if self.device_listener:
                try:
                    self.device_listener.stop()
                    print("Conexion serial detenida")
                except:
                    pass

            self.user_manager.logout()
            self.master.show_login()
            return

        frame = self.frames[name]
        frame.pack(fill="both", expand=True)

        if name == "Dispositivos":
            frame.refresh()
        elif name == "Telegram":
            # Actualizar el bot en el frame de Telegram
            if hasattr(frame, 'telegram_bot'):
                frame.telegram_bot = self.telegram_bot
                # Asegurar que el bot tenga el user_manager actualizado
                if self.telegram_bot:
                    self.telegram_bot.user_manager = self.user_manager
                    print(f"Bot actualizado en frame. Usuario: {self.user_manager.current_user}")

                if hasattr(frame, '_update_status'):
                    frame._update_status()

    def _on_device_added(self, device):
        self.select_tab("Dispositivos")

    def open_device_detail(self, device):
        """Abre la ventana de detalle para un dispositivo"""
        # Intentar importar SecurityController para pasarlo si está disponible
        security_controller = None
        try:
            from controllers.security_controller import SecurityController
            if TELEGRAM_AVAILABLE and self.telegram_bot:
                security_controller = SecurityController(self.user_manager,
                                                         "8587676832:AAHx9szhD1mjCJXzlHHN81aR90aPh3j7w-I")
        except ImportError:
            security_controller = None

        DeviceDetailWindow(
            self.master,
            device,
            self.device_manager,
            self._refresh_devices,
            DEVICE_TYPES,
            security_controller  # ← Solo si está disponible
        )

    def _refresh_devices(self):
        f = self.frames.get("Dispositivos")
        if f:
            f.refresh()

    def destroy(self):
        if self.device_listener:
            try:
                self.device_listener.stop()
            except:
                pass

        super().destroy()
