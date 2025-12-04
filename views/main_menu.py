"""
Menú principal de la aplicación con sistema de pestañas
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
from config import COLORS, DEVICE_TYPES

from views.devices_frame import DevicesFrame
from views.add_device_frame import AddDeviceFrame
from views.device_detail_window import DeviceDetailWindow

from controllers.security_controller import SecurityController


class MainMenu(tk.Frame):
    """Frame principal con navegación por pestañas"""
    
    def __init__(self, master, device_manager, user_manager):
        super().__init__(master)
        self.master = master
        self.device_manager = device_manager
        self.user_manager = user_manager
        self.configure(bg=COLORS["background"])
        
        # Token de Telegram (TODO: mover a configuración)
        TELEGRAM_TOKEN = "8587676832:AAHx9szhD1mjCJXzlHHN81aR90aPh3j7w-I"
        
        # Inicializar controlador de seguridad
        self.security_controller = SecurityController(user_manager, TELEGRAM_TOKEN)
        
        # Configurar callbacks
        self.security_controller.set_event_callback(self._on_security_event)
        self.security_controller.set_alert_callback(self._show_alert)

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

        # Iniciar procesamiento de mensajes
        self._process_messages()

        self.select_tab("Dispositivos")
    
    def _process_messages(self):
        """Procesa mensajes del hardware periódicamente"""
        try:
            self.security_controller.process_hardware_messages()
        except Exception as e:
            print(f"Error procesando mensajes: {e}")
        
        # Llamar de nuevo en 100ms
        self.after(100, self._process_messages)
    
    def _on_security_event(self, event):
        """Callback cuando hay un evento de seguridad"""
        # Agregar al historial
        self._add_to_history(event['message'], event['type'])
    
    def _show_alert(self, title, message):
        """Muestra una alerta visual"""
        if "ALARMA" in message or "🚨" in message:
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
    
    def _create_history_frame(self):
        """Crea el frame de historial de eventos"""
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
        self.history_text.tag_config("motion", foreground="#2196F3")
        self.history_text.tag_config("smoke", foreground="#FF5722")
        self.history_text.tag_config("panic", foreground="#F44336")
        self.history_text.tag_config("door", foreground="#FF9800")
        self.history_text.tag_config("laser", foreground="#9C27B0")
        self.history_text.tag_config("lock", foreground="#4CAF50")
        self.history_text.tag_config("system", foreground="#00BCD4")
        
        # Deshabilitar edición
        self.history_text.config(state="disabled")
        
        # Agregar mensaje inicial
        self._add_to_history("Sistema iniciado", "system")
        
        return history_frame
    
    def _add_to_history(self, mensaje, tipo="system"):
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
            self._add_to_history("Historial limpiado", "system")
    
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

        # Obtener estado actual
        connection_status = self.security_controller.get_connection_status()
        
        # Estado Raspberry Pi
        serial_status = "✅ Conectado" if connection_status['serial'] else "❌ Desconectado"
        tk.Label(
            status_frame,
            text=f"Raspberry Pi: {serial_status}",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=3)

        # Estado Telegram
        telegram_status = "✅ Conectado" if connection_status['telegram'] else "❌ Desconectado"
        tk.Label(
            status_frame,
            text=f"Bot Telegram: {telegram_status}",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=3)

        # Botón para vincular Telegram
        if connection_status['telegram']:
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
        success, message, chat_id = self.security_controller.link_telegram_account()
        
        if success:
            messagebox.showinfo("Vinculación exitosa", message)
        else:
            messagebox.showinfo("Instrucciones", message)

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
        self.select_tab("Dispositivos")

    def open_device_detail(self, device):
        """Abre la ventana de detalle para un dispositivo"""
        DeviceDetailWindow(
            self.master, 
            device, 
            self.device_manager, 
            self._refresh_devices, 
            DEVICE_TYPES,
            self.security_controller  # ← NUEVO: pasar el controlador
        )

    def _refresh_devices(self):
        """Refresca el frame de dispositivos"""
        f = self.frames.get("Dispositivos")
        if f:
            f.refresh()