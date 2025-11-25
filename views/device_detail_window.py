"""
Ventana de detalle para ver y editar información de un dispositivo
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import time
from config import COLORS, DAYS_OF_WEEK


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
        self.geometry("620x720")
        self.config(bg=COLORS["background"])
        self.device = device
        self.device_manager = device_manager
        self.refresh_callback = refresh_callback
        self.tipos_list = tipos_list
        self.day_buttons = {}
        self.hour_buttons = {}
        self.active = device.get("active", False)

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
        # Escribir en historial
        self._append_history(f"Estado cambiado a {'Activado' if self.active else 'Desactivado'}")
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

    def _on_close(self):
        """Cierra la ventana y actualiza la vista padre"""
        # Aseguramos actualizar la vista padre antes de cerrar
        self.refresh_callback()
        self.destroy()
