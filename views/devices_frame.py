"""
Frame principal que muestra todos los dispositivos organizados por zonas
"""

import tkinter as tk
from tkinter import ttk
from config import COLORS
from .device_widget import DeviceWidget


class DevicesFrame(tk.Frame):
    """Frame que muestra la lista de dispositivos organizados por zonas con scroll"""
    
    def __init__(self, master, device_manager, open_detail_callback):
        super().__init__(master, bg=COLORS["background"])
        self.device_manager = device_manager
        self.open_detail_callback = open_detail_callback
        self.zone_frames = {}  # zona -> frame contenedor y widgets

        # Canvas + scrollbar vertical
        self.canvas = tk.Canvas(self, bg=COLORS["background"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=COLORS["background"])
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Bind para resize
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        """Ajustar width del inner window para usar todo el ancho disponible"""
        canvas_width = event.width
        self.canvas.itemconfigure(self.inner_id, width=canvas_width)

    def refresh(self):
        """Reconstruye toda la vista de dispositivos según el estado actual"""
        # Destruir todo y reconstruir según device_manager
        for widget in self.inner.winfo_children():
            widget.destroy()
        self.zone_frames = {}

        zones = self.device_manager.get_zones()
        for zone in zones:
            devices = self.device_manager.devices_by_zone.get(zone, [])
            # Crear labelframe por zona
            lf = tk.LabelFrame(
                self.inner, 
                text=zone, 
                bg=COLORS["background"], 
                fg=COLORS["primary"],
                font=("Arial", 12, "bold"), 
                padx=8, 
                pady=8
            )
            lf.pack(fill="x", pady=8, padx=10)
            
            # Dentro de lf, crear un frame que contendrá los device widgets con wrapping en 2 columnas
            container = tk.Frame(lf, bg=COLORS["background"])
            container.pack(fill="x")
            
            # Colocamos widgets en una grilla de 2 columnas
            col_count = 2
            r = 0
            c = 0
            for dev in devices:
                w = DeviceWidget(container, dev, self.open_detail_callback)
                w.grid(row=r, column=c, padx=8, pady=6)
                
                # Mantener referencia
                if zone not in self.zone_frames:
                    self.zone_frames[zone] = []
                self.zone_frames[zone].append((dev, w))
                
                c += 1
                if c >= col_count:
                    c = 0
                    r += 1

    def find_widget_for_device(self, device):
        """Busca el widget asociado a un dispositivo"""
        zone = device["zona"]
        if zone in self.zone_frames:
            for dev, widget in self.zone_frames[zone]:
                if dev is device or dev.get("id") == device.get("id"):
                    return widget
        return None

    def remove_device_widget(self, device):
        """Remueve el widget de un dispositivo (simplificado: refresca todo)"""
        self.refresh()
