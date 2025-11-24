"""
Widget personalizado para mostrar un dispositivo como un botón clickeable
"""

import tkinter as tk
from config import COLORS


class DeviceWidget(tk.Frame):
    """
    Frame que representa un "botón" de dispositivo
    con texto grande (ID) y texto pequeño abajo-derecha (tipo)
    y que responde a click para abrir detalle.
    """
    
    def __init__(self, master, device, open_callback, *args, **kwargs):
        super().__init__(master, bg=COLORS["secondary"], bd=0, relief="flat", *args, **kwargs)
        self.device = device
        self.open_callback = open_callback

        # Tamaño y estilo
        self.config(width=160, height=90)
        # Frame no ajusta tamaño automáticamente
        self.pack_propagate(False)

        # ID grande centrado
        self.id_label = tk.Label(
            self, 
            text=device["id"], 
            bg=COLORS["secondary"], 
            fg=COLORS["text_light"],
            font=("Arial", 12, "bold")
        )
        self.id_label.pack(expand=True)

        # Label pequeño bottom-right para tipo
        self.type_label = tk.Label(
            self, 
            text=device["tipo"], 
            bg=COLORS["secondary"], 
            fg="#dcdcdc",
            font=("Arial", 8)
        )
        # Colocamos en la esquina inferior derecha usando place
        self.type_label.place(relx=1.0, rely=1.0, anchor="se", x=-6, y=-6)

        # Bind click en toda la widget
        self.bind("<Button-1>", lambda e: open_callback(self.device))
        self.id_label.bind("<Button-1>", lambda e: open_callback(self.device))
        self.type_label.bind("<Button-1>", lambda e: open_callback(self.device))

    def update_display(self):
        """Actualiza la visualización del dispositivo"""
        self.id_label.config(text=self.device["id"])
        self.type_label.config(text=self.device["tipo"])
