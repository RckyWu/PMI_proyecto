"""
Controlador principal de la aplicacion
Maneja el flujo entre diferentes pantallas
"""

import tkinter as tk
from config import WINDOW_CONFIG, COLORS
from models import DeviceManager, UserManager
from views import SplashScreen, LoginScreen, RegisterScreen, MainMenu
from controllers.serial_comm import init_serial, close_serial


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(WINDOW_CONFIG["title"])
        self.geometry(f"{WINDOW_CONFIG['width']}x{WINDOW_CONFIG['height']}")
        self.resizable(WINDOW_CONFIG["resizable"], WINDOW_CONFIG["resizable"])
        self.configure(bg=COLORS["background"])

        self.device_manager = DeviceManager()
        self.user_manager = UserManager()

        self.serial_connected = init_serial(puerto="COM5", baud=115200)
        if not self.serial_connected:
            print("Advertencia: No se pudo conectar al puerto serial")

        self.withdraw()
        self.splash = SplashScreen(self, self.show_login)

    def show_login(self):
        self.deiconify()
        self._switch_frame(LoginScreen(self, self.show_register, self.show_menu, self.user_manager))

    def show_register(self):
        self._switch_frame(RegisterScreen(self, self.show_login, self.user_manager))

    def show_menu(self):
        devices_file = self.user_manager.get_user_devices_file()
        self.device_manager.set_devices_file(devices_file)

        self._switch_frame(MainMenu(self, self.device_manager, self.user_manager))

    def _switch_frame(self, frame):
        if hasattr(self, "current_frame") and self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame
        self.current_frame.pack(fill="both", expand=True)

    def destroy(self):
        close_serial()
        super().destroy()