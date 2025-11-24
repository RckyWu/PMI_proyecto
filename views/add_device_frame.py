"""
Frame para agregar nuevos dispositivos
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, DEVICE_TYPES


class AddDeviceFrame(tk.Frame):
    """Frame para agregar un nuevo dispositivo al sistema"""
    
    def __init__(self, master, add_callback, device_manager):
        super().__init__(master, bg=COLORS["background"])
        self.add_callback = add_callback
        self.device_manager = device_manager

        # Título
        tk.Label(
            self, 
            text="Agregar Dispositivo", 
            bg=COLORS["background"], 
            fg=COLORS["primary"],
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        # Tipo de dispositivo
        tk.Label(
            self, 
            text="Tipo de dispositivo:", 
            bg=COLORS["background"], 
            fg=COLORS["primary"]
        ).pack()
        
        self.tipo_var = tk.StringVar()
        self.tipo_dropdown = ttk.Combobox(
            self, 
            textvariable=self.tipo_var, 
            values=DEVICE_TYPES,
            state="readonly", 
            width=40
        )
        self.tipo_dropdown.pack(pady=5)

        # ID del dispositivo
        tk.Label(
            self, 
            text="ID de dispositivo:", 
            bg=COLORS["background"], 
            fg=COLORS["primary"]
        ).pack()
        self.id_entry = tk.Entry(self, width=35)
        self.id_entry.pack(pady=5)

        # Zona
        tk.Label(
            self, 
            text="Zona:", 
            bg=COLORS["background"], 
            fg=COLORS["primary"]
        ).pack()
        self.zona_entry = tk.Entry(self, width=35)
        self.zona_entry.pack(pady=5)

        # Botón para agregar
        tk.Button(
            self, 
            text="Agregar Dispositivo", 
            bg=COLORS["primary"], 
            fg=COLORS["text_light"],
            command=self._on_add
        ).pack(pady=15)

    def _on_add(self):
        """Procesa la adición de un nuevo dispositivo"""
        tipo = self.tipo_var.get()
        device_id = self.id_entry.get().strip()
        zona = self.zona_entry.get().strip()

        if not tipo or not device_id or not zona:
            messagebox.showwarning("Campos incompletos", "Por favor complete todos los campos.")
            return

        device = {"id": device_id, "tipo": tipo, "zona": zona, "active": False}
        self.device_manager.add_device(device)
        self.add_callback(device)
        messagebox.showinfo("Agregado", f"Dispositivo '{device_id}' agregado correctamente.")
        
        # Limpiar campos
        self.tipo_var.set("")
        self.id_entry.delete(0, tk.END)
        self.zona_entry.delete(0, tk.END)
