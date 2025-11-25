"""
Controlador principal de la aplicación
Maneja el flujo entre diferentes pantallas
"""

import tkinter as tk
from config import WINDOW_CONFIG, COLORS
from models import DeviceManager, UserManager
from views import SplashScreen, LoginScreen, RegisterScreen, MainMenu


class App(tk.Tk):
    """Aplicación principal - Controlador de la interfaz"""
    
    def __init__(self):
        super().__init__()
        self.title(WINDOW_CONFIG["title"])
        self.geometry(f"{WINDOW_CONFIG['width']}x{WINDOW_CONFIG['height']}")
        self.resizable(WINDOW_CONFIG["resizable"], WINDOW_CONFIG["resizable"])
        self.configure(bg=COLORS["background"])

        # Gestores compartidos
        self.device_manager = DeviceManager()  # Sin archivo inicialmente
        self.user_manager = UserManager()

        # Inicialmente ocultar ventana principal para mostrar splash
        self.withdraw()
        self.splash = SplashScreen(self, self.show_login)

    def show_login(self):
        """Muestra la pantalla de login"""
        self.deiconify()
        self._switch_frame(LoginScreen(self, self.show_register, self.show_menu, self.user_manager))

    def show_register(self):
        """Muestra la pantalla de registro"""
        self._switch_frame(RegisterScreen(self, self.show_login, self.user_manager))

    def show_menu(self):
        """Muestra el menú principal"""
        # Cargar dispositivos del usuario actual
        devices_file = self.user_manager.get_user_devices_file()
        self.device_manager.set_devices_file(devices_file)
        
        self._switch_frame(MainMenu(self, self.device_manager, self.user_manager))

    def _switch_frame(self, frame):
        """Cambia entre frames principales destruyendo el anterior"""
        if hasattr(self, "current_frame") and self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame
        self.current_frame.pack(fill="both", expand=True)