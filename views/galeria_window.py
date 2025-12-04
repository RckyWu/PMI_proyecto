"""
Ventana de galería para ver capturas guardadas
"""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from PIL import Image, ImageTk
from config import COLORS


class GaleriaWindow(tk.Toplevel):
    """Ventana para mostrar galería de imágenes capturadas"""
    
    def __init__(self, master, carpeta, titulo="Galería"):
        super().__init__(master)
        self.title(titulo)
        self.geometry("850x650")
        self.config(bg=COLORS["background"])
        
        self.carpeta = Path(carpeta)
        self.imagenes = []
        self.indice_actual = 0
        
        self._crear_widgets()
        self._cargar_imagenes()
        
        if self.imagenes:
            self._mostrar_imagen_actual()
        else:
            self.label_info.config(text="📭 No hay capturas guardadas en esta carpeta")
    
    def _crear_widgets(self):
        """Crea los widgets de la ventana"""
        # Título
        tk.Label(
            self,
            text="📷 Galería de Capturas",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 5))
        
        # Frame para la imagen
        self.frame_imagen = tk.Frame(self, bg="#2b2b2b", relief="sunken", bd=2)
        self.frame_imagen.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.label_imagen = tk.Label(self.frame_imagen, bg="#2b2b2b")
        self.label_imagen.pack(expand=True)
        
        # Info de la imagen
        self.label_info = tk.Label(
            self,
            text="Cargando...",
            bg=COLORS["background"],
            font=("Arial", 10),
            fg=COLORS["text_dark"]
        )
        self.label_info.pack(pady=(5, 10))
        
        # Controles de navegación
        controles = tk.Frame(self, bg=COLORS["background"])
        controles.pack(pady=10)
        
        self.btn_anterior = tk.Button(
            controles,
            text="◀️ Anterior",
            command=self._imagen_anterior,
            bg=COLORS["primary"],
            fg="white",
            font=("Arial", 10, "bold"),
            width=14,
            cursor="hand2"
        )
        self.btn_anterior.pack(side="left", padx=5)
        
        self.btn_eliminar = tk.Button(
            controles,
            text="🗑️ Eliminar",
            command=self._eliminar_actual,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            width=14,
            cursor="hand2"
        )
        self.btn_eliminar.pack(side="left", padx=5)
        
        tk.Button(
            controles,
            text="📂 Abrir Carpeta",
            command=self._abrir_carpeta,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            width=14,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        self.btn_siguiente = tk.Button(
            controles,
            text="Siguiente ▶️",
            command=self._imagen_siguiente,
            bg=COLORS["primary"],
            fg="white",
            font=("Arial", 10, "bold"),
            width=14,
            cursor="hand2"
        )
        self.btn_siguiente.pack(side="left", padx=5)
        
        # Botón cerrar
        tk.Button(
            self,
            text="✖️ Cerrar",
            command=self.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Arial", 10),
            width=12
        ).pack(pady=(0, 10))
    
    def _cargar_imagenes(self):
        """Carga la lista de imágenes de la carpeta"""
        if self.carpeta.exists():
            # Cargar en orden inverso (más recientes primero)
            self.imagenes = sorted(
                self.carpeta.glob("*.jpg"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            print(f"📸 {len(self.imagenes)} imágenes encontradas en {self.carpeta}")
        else:
            print(f"⚠️ Carpeta no existe: {self.carpeta}")
    
    def _mostrar_imagen_actual(self):
        """Muestra la imagen en el índice actual"""
        if not self.imagenes:
            self.label_imagen.config(image="", text="No hay imágenes")
            self.label_info.config(text="📭 No hay capturas guardadas")
            self.btn_anterior.config(state=tk.DISABLED)
            self.btn_siguiente.config(state=tk.DISABLED)
            self.btn_eliminar.config(state=tk.DISABLED)
            return
        
        try:
            ruta = self.imagenes[self.indice_actual]
            
            # Cargar y redimensionar imagen
            img = Image.open(ruta)
            
            # Redimensionar manteniendo aspecto (max 750x500)
            img.thumbnail((750, 500), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.label_imagen.config(image=photo, text="")
            self.label_imagen.image = photo  # Mantener referencia
            
            # Actualizar info
            fecha = ruta.stat().st_mtime
            from datetime import datetime
            fecha_str = datetime.fromtimestamp(fecha).strftime("%Y-%m-%d %H:%M:%S")
            
            info_text = f"📷 Imagen {self.indice_actual + 1} de {len(self.imagenes)} | {ruta.name} | 📅 {fecha_str}"
            self.label_info.config(text=info_text)
            
            # Habilitar/deshabilitar botones
            self.btn_anterior.config(state=tk.NORMAL if len(self.imagenes) > 1 else tk.DISABLED)
            self.btn_siguiente.config(state=tk.NORMAL if len(self.imagenes) > 1 else tk.DISABLED)
            self.btn_eliminar.config(state=tk.NORMAL)
            
        except Exception as e:
            print(f"❌ Error mostrando imagen: {e}")
            self.label_info.config(text=f"❌ Error: {e}")
            self.label_imagen.config(image="", text="Error cargando imagen")
    
    def _imagen_anterior(self):
        """Muestra la imagen anterior"""
        if self.imagenes and len(self.imagenes) > 0:
            self.indice_actual = (self.indice_actual - 1) % len(self.imagenes)
            self._mostrar_imagen_actual()
    
    def _imagen_siguiente(self):
        """Muestra la imagen siguiente"""
        if self.imagenes and len(self.imagenes) > 0:
            self.indice_actual = (self.indice_actual + 1) % len(self.imagenes)
            self._mostrar_imagen_actual()
    
    def _eliminar_actual(self):
        """Elimina la imagen actual"""
        if not self.imagenes:
            return
        
        ruta = self.imagenes[self.indice_actual]
        respuesta = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Deseas eliminar esta captura?\n\n{ruta.name}\n\nEsta acción no se puede deshacer."
        )
        
        if respuesta:
            try:
                ruta.unlink()  # Eliminar archivo
                print(f"🗑️ Eliminado: {ruta.name}")
                
                # Remover de la lista
                self.imagenes.pop(self.indice_actual)
                
                if self.imagenes:
                    # Ajustar índice si es necesario
                    if self.indice_actual >= len(self.imagenes):
                        self.indice_actual = len(self.imagenes) - 1
                    self._mostrar_imagen_actual()
                else:
                    # No quedan imágenes
                    self.label_info.config(text="📭 No quedan capturas")
                    self.label_imagen.config(image="", text="No hay más imágenes")
                    self.btn_anterior.config(state=tk.DISABLED)
                    self.btn_siguiente.config(state=tk.DISABLED)
                    self.btn_eliminar.config(state=tk.DISABLED)
                
                messagebox.showinfo("Eliminado", "Captura eliminada exitosamente")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")
    
    def _abrir_carpeta(self):
        """Abre la carpeta de capturas en el explorador"""
        import os
        import sys
        import subprocess
        
        carpeta_str = str(self.carpeta.absolute())
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(carpeta_str)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', carpeta_str])
            else:  # Linux
                subprocess.call(['xdg-open', carpeta_str])
            
            print(f"📂 Abriendo carpeta: {carpeta_str}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{e}")
