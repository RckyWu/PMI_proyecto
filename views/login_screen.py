"""
Pantalla de inicio de sesión
"""

import tkinter as tk
from config import COLORS


class LoginScreen(tk.Frame):
    """Frame para el inicio de sesión de usuarios"""
    
    def __init__(self, master, go_to_register, go_to_menu):
        super().__init__(master)
        self.master = master
        self.go_to_register = go_to_register
        self.go_to_menu = go_to_menu
        self.configure(bg=COLORS["background"])

        # Título
        tk.Label(
            self, 
            text="Iniciar Sesión", 
            bg=COLORS["background"], 
            font=("Arial", 18, "bold")
        ).pack(pady=20)

        # Campo de correo
        tk.Label(self, text="Correo:", bg=COLORS["background"]).pack()
        self.email_entry = tk.Entry(self, width=30)
        self.email_entry.pack(pady=5)

        # Campo de contraseña
        tk.Label(self, text="Contraseña:", bg=COLORS["background"]).pack()
        self.password_entry = tk.Entry(self, show="*", width=30)
        self.password_entry.pack(pady=5)

        # Botón de inicio de sesión
        tk.Button(
            self, 
            text="Iniciar Sesión", 
            width=20, 
            bg=COLORS["primary"], 
            fg=COLORS["text_light"],
            command=self._iniciar_sesion
        ).pack(pady=15)

        # Link a registro
        tk.Label(
            self, 
            text="¿No tiene cuenta?", 
            bg=COLORS["background"]
        ).pack(pady=(30, 0))
        
        tk.Button(
            self, 
            borderwidth=0, 
            text="Registrarse", 
            bg=COLORS["background"], 
            fg=COLORS["danger"],
            command=self.go_to_register
        ).pack(pady=5)

    def _iniciar_sesion(self):
        """Procesa el inicio de sesión (demo: siempre permite acceso)"""
        # En una aplicación real, aquí se validarían las credenciales
        self.go_to_menu()
