"""
Pantalla de registro de nuevos usuarios
"""

import tkinter as tk
from tkinter import messagebox
from config import COLORS


class RegisterScreen(tk.Frame):
    """Frame para el registro de nuevos usuarios"""
    
    def __init__(self, master, go_to_login, user_manager):
        super().__init__(master)
        self.master = master
        self.go_to_login = go_to_login
        self.user_manager = user_manager  # ← NUEVO
        self.configure(bg=COLORS["background"])

        # Título
        tk.Label(
            self, 
            text="Crear Cuenta", 
            bg=COLORS["background"], 
            fg=COLORS["primary"], 
            font=("Arial", 18, "bold")
        ).pack(pady=15)

        # Campo de correo
        tk.Label(self, fg=COLORS["primary"], text="Correo:", bg=COLORS["background"]).pack()
        self.email_entry = tk.Entry(self, width=30)
        self.email_entry.pack(pady=3)

        # Campo de Telegram
        tk.Label(self, fg=COLORS["primary"], text="Telegram:", bg=COLORS["background"]).pack()
        self.telegram_entry = tk.Entry(self, width=30)
        self.telegram_entry.pack(pady=3)

        # Campo de contraseña
        tk.Label(self, fg=COLORS["primary"], text="Contraseña:", bg=COLORS["background"]).pack()
        self.password_entry = tk.Entry(self, show="*", width=30)
        self.password_entry.pack(pady=3)

        # Campo de confirmación de contraseña
        tk.Label(self, fg=COLORS["primary"], text="Confirmar contraseña:", bg=COLORS["background"]).pack()
        self.confirm_entry = tk.Entry(self, show="*", width=30)
        self.confirm_entry.pack(pady=3)

        # Reglas de contraseña
        reglas = [
            "• Mínimo 4 caracteres",
            "• Al menos 1 letra mayúscula",
            "• Incluir al menos 1 número"
        ]
        tk.Label(
            self, 
            text="Requisitos de la contraseña:", 
            bg=COLORS["background"], 
            fg=COLORS["primary"],
            font=("Arial", 10, "bold")
        ).pack(pady=8)
        
        for regla in reglas:
            tk.Label(
                self, 
                text=regla, 
                bg=COLORS["background"], 
                fg=COLORS["accent"]
            ).pack(anchor="w", padx=80)

        # Botón de crear cuenta
        tk.Button(
            self, 
            text="Crear cuenta", 
            bg=COLORS["danger"], 
            fg=COLORS["text_light"],
            command=self._crear_cuenta
        ).pack(pady=12)

    def _crear_cuenta(self):
        """Procesa la creación de cuenta guardando en JSON"""
        email = self.email_entry.get().strip()
        telegram = self.telegram_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        
        if not email or not telegram or not password or not confirm:
            messagebox.showwarning("Campos vacíos", "Por favor complete todos los campos")
            return
        
        if password != confirm:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return
        
        success, message = self.user_manager.register(email, password, telegram)
        
        if success:
            messagebox.showinfo("Éxito", message)
            self.go_to_login()
        else:
            messagebox.showerror("Error", message)