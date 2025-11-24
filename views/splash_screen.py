"""
Splash screen - Pantalla de carga inicial
"""

import tkinter as tk
import threading
import time
from config import COLORS, SPLASH_CONFIG


class SplashScreen(tk.Toplevel):
    """Pantalla de presentación al iniciar la aplicación"""
    
    def __init__(self, master, next_screen_callback):
        super().__init__(master)
        self.next_screen_callback = next_screen_callback
        self.overrideredirect(True)  # Sin bordes
        self.configure(bg=COLORS["background"])

        w, h = SPLASH_CONFIG["width"], SPLASH_CONFIG["height"]
        # Centrar en pantalla
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Espacio para logo
        tk.Label(
            self, 
            text="LOGO AQUÍ", 
            bg=COLORS["background"], 
            fg=COLORS["primary"],
            font=("Arial", 26, "bold")
        ).pack(expand=True)

        # Subtexto
        tk.Label(
            self, 
            text="Cargando aplicación...", 
            bg=COLORS["background"], 
            fg=COLORS["accent"],
            font=("Arial", 10)
        ).pack(pady=(0, 20))

        # Cerrar después de algunos segundos en hilo para no bloquear UI
        threading.Thread(target=self._wait_and_continue, daemon=True).start()

    def _wait_and_continue(self):
        """Espera y luego continúa a la siguiente pantalla"""
        time.sleep(SPLASH_CONFIG["duration"])
        try:
            self.destroy()
        except tk.TclError:
            pass
        self.next_screen_callback()
