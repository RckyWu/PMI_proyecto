"""
Splash screen - Pantalla de carga inicial
"""


import contextlib
import tkinter as tk
import threading
import time
from config import COLORS, SPLASH_CONFIG

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


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

        # Intentar cargar logo
        self._load_logo()

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

    def _load_logo(self):
        """Intenta cargar y mostrar el logo de la aplicación"""
        logo_loaded = False
        
        # Intentar cargar logo en diferentes formatos y ubicaciones
        logo_paths = [
            "Seguridad-Ving-logo.png",
            "Seguridad-Ving-logo.ppm",
            "assets/Seguridad-Ving-logo.png",
            "assets/logo.png"
        ]
        
        if PIL_AVAILABLE:
            for logo_path in logo_paths:
                try:
                    # Cargar logo
                    logo_image = Image.open(logo_path)
                    
                    # Redimensionar manteniendo aspecto (max 200x120)
                    logo_image.thumbnail((200, 120), Image.Resampling.LANCZOS)
                    
                    # Convertir a PhotoImage
                    logo_photo = ImageTk.PhotoImage(logo_image)
                    
                    # Crear label con imagen
                    logo_label = tk.Label(
                        self,
                        image=logo_photo,
                        bg=COLORS["background"],
                        bd=0
                    )
                    logo_label.image = logo_photo  # Mantener referencia
                    logo_label.pack(expand=True, pady=20)
                    
                    logo_loaded = True
                    break  # Logo cargado exitosamente
                    
                except Exception:
                    continue  # Probar siguiente ruta
        
        # Fallback: Mostrar texto si no se pudo cargar el logo
        if not logo_loaded:
            tk.Label(
                self, 
                text="VING", 
                bg=COLORS["background"], 
                fg=COLORS["primary"],
                font=("Arial", 32, "bold")
            ).pack(expand=True, pady=20)
            
            tk.Label(
                self, 
                text="Seguridad Inteligente", 
                bg=COLORS["background"], 
                fg=COLORS["secondary"],
                font=("Arial", 12)
            ).pack()

    def _wait_and_continue(self):
        """Espera y luego continúa a la siguiente pantalla"""
        time.sleep(SPLASH_CONFIG["duration"])
        with contextlib.suppress(tk.TclError):
            self.destroy()
        self.next_screen_callback()
