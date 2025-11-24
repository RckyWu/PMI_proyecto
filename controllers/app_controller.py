"""
Controlador principal de la aplicación
Maneja el flujo entre diferentes pantallas
"""

import tkinter as tk
from config import WINDOW_CONFIG, COLORS
from models import DeviceManager
from views import SplashScreen, LoginScreen, RegisterScreen, MainMenu


class App(tk.Tk):
    """Aplicación principal - Controlador de la interfaz"""
    
    def __init__(self):
        super().__init__()
        self.title(WINDOW_CONFIG["title"])
        self.geometry(f"{WINDOW_CONFIG['width']}x{WINDOW_CONFIG['height']}")
        self.resizable(WINDOW_CONFIG["resizable"], WINDOW_CONFIG["resizable"])
        self.configure(bg=COLORS["background"])

        # Gestor de dispositivos compartido
        self.device_manager = DeviceManager()

        # Inicialmente ocultar ventana principal para mostrar splash
        self.withdraw()
        self.splash = SplashScreen(self, self.show_login)

    def show_login(self):
        """Muestra la pantalla de login"""
        self.deiconify()
        self._switch_frame(LoginScreen(self, self.show_register, self.show_menu))

    def show_register(self):
        """Muestra la pantalla de registro"""
        self._switch_frame(RegisterScreen(self, self.show_login))

    def show_menu(self):
        """Muestra el menú principal"""
        self._switch_frame(MainMenu(self, self.device_manager))

    def _switch_frame(self, frame):
        """Cambia entre frames principales destruyendo el anterior"""
        # Destruir frame anterior si existe
        if hasattr(self, "current_frame") and self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame
        self.current_frame.pack(fill="both", expand=True)
