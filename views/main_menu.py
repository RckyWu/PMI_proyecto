"""
Menú principal de la aplicación con sistema de pestañas
"""

import tkinter as tk
from config import COLORS, DEVICE_TYPES
from .devices_frame import DevicesFrame
from .add_device_frame import AddDeviceFrame
from .device_detail_window import DeviceDetailWindow


class MainMenu(tk.Frame):
    """Frame principal con navegación por pestañas"""
    
    def __init__(self, master, device_manager):
        super().__init__(master)
        self.master = master
        self.device_manager = device_manager
        self.configure(bg=COLORS["background"])

        # Pestañas superiores
        self.tab_frame = tk.Frame(self, bg=COLORS["primary"])
        self.tab_frame.pack(fill="x")

        self.tabs = ["Dispositivos", "Historial", "Agregar", "Cerrar Sesión"]
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
            text="Historial general (vacío por ahora)", 
            bg=COLORS["background"]
        ).pack(pady=20)

        self.select_tab("Dispositivos")

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
            # Volver a login (master es App)
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
