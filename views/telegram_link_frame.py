"""
Frame para vinculación con Telegram
Versión que mantiene tu interfaz original funcionando
y agrega compatibilidad con SecurityController
"""

import tkinter as tk
from tkinter import messagebox
import webbrowser
from pathlib import Path
from config import COLORS

# Intentar importar PIL para cargar imágenes PNG
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Advertencia: PIL no disponible. Instalar con: pip install Pillow")


class TelegramLinkFrame(tk.Frame):
    """Frame para vincular cuenta de Telegram con el sistema"""

    def __init__(self, master, user_manager, telegram_bot=None, security_controller=None):
        super().__init__(master, bg=COLORS["background"])
        self.master = master
        self.user_manager = user_manager
        self.telegram_bot = telegram_bot
        self.security_controller = security_controller  # ← Nuevo: compatibilidad con SecurityController
        self.current_user = user_manager.current_user if user_manager else None

        self._create_widgets()
        self._update_status()

    def _create_widgets(self):
        # Frame principal con dos columnas
        main_container = tk.Frame(self, bg=COLORS["background"])
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Columna izquierda: QR e Instrucciones
        left_column = tk.Frame(main_container, bg=COLORS["background"])
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Columna derecha: Registro y Estado
        right_column = tk.Frame(main_container, bg=COLORS["background"])
        right_column.pack(side="right", fill="both", expand=True)

        # Título (sobre ambas columnas)
        tk.Label(
            self,
            text="Vinculación con Telegram",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 16, "bold")
        ).pack(pady=(5, 10))

        # Información del usuario
        if self.current_user:
            user_frame = tk.Frame(self, bg=COLORS["background"])
            user_frame.pack(pady=(0, 10))

            tk.Label(
                user_frame,
                text=f"Usuario: {self.current_user}",
                bg=COLORS["background"],
                fg=COLORS["text_dark"],
                font=("Arial", 11)
            ).pack()

        # ========== COLUMNA IZQUIERDA ==========

        # QR del bot
        self._create_qr_section(left_column)

        # Instrucciones
        self._create_instructions(left_column)

        # ========== COLUMNA DERECHA ==========

        # Botones de registro
        self._create_registration_buttons(right_column)

        # Botones de prueba
        self._create_test_buttons(right_column)

        # Estado actual
        self._create_status_section(right_column)

    def _create_qr_section(self, parent):
        qr_frame = tk.LabelFrame(
            parent,
            text="Escanear Código QR",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        qr_frame.pack(fill="x", pady=(0, 10))

        # Contenedor para el QR
        qr_container = tk.Frame(qr_frame, bg="white")
        qr_container.pack(pady=5)

        # Buscar imagen QR.png (o QR.ppm como fallback)
        qr_png_path = Path(__file__).parent.parent / "QR.png"
        qr_ppm_path = Path(__file__).parent.parent / "QR.ppm"
        
        # También buscar en el directorio actual por si acaso
        if not qr_png_path.exists():
            qr_png_path = Path("QR.png")
        if not qr_ppm_path.exists():
            qr_ppm_path = Path("QR.ppm")

        qr_loaded = False
        
        # Intentar cargar PNG con PIL
        if qr_png_path.exists() and PIL_AVAILABLE:
            try:
                # Cargar imagen PNG con PIL
                pil_image = Image.open(str(qr_png_path))
                
                # Redimensionar si es muy grande
                max_size = 150
                if pil_image.width > max_size or pil_image.height > max_size:
                    pil_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convertir a PhotoImage de Tkinter
                qr_photo = ImageTk.PhotoImage(pil_image)

                qr_label = tk.Label(qr_container, image=qr_photo, bg="white")
                qr_label.image = qr_photo  # Mantener referencia
                qr_label.pack()
                qr_loaded = True
                print(f"QR.png cargado correctamente desde: {qr_png_path}")

            except Exception as e:
                print(f"Error cargando QR.png: {e}")
        
        # Fallback: intentar cargar PPM si PNG no funcionó
        if not qr_loaded and qr_ppm_path.exists():
            try:
                qr_photo = tk.PhotoImage(file=str(qr_ppm_path))

                # Reducir tamaño si es muy grande
                img_width = qr_photo.width()
                max_size = 150

                if img_width > max_size:
                    factor = 2 if img_width > max_size * 2 else 1
                    qr_photo = qr_photo.subsample(factor, factor)

                qr_label = tk.Label(qr_container, image=qr_photo, bg="white")
                qr_label.image = qr_photo
                qr_label.pack()
                qr_loaded = True
                print(f"QR.ppm cargado correctamente desde: {qr_ppm_path}")

            except Exception as e:
                print(f"Error cargando QR.ppm: {e}")
        
        # Si no se pudo cargar ninguna imagen, mostrar fallback
        if not qr_loaded:
            self._create_qr_fallback(qr_container)
            if not PIL_AVAILABLE:
                print("PIL no disponible. Instala Pillow: pip install Pillow")
            else:
                print(f"No se encontró QR.png en: {qr_png_path}")
                print(f"No se encontró QR.ppm en: {qr_ppm_path}")

        # Nombre del bot
        tk.Label(
            qr_frame,
            text="@VingSecurityBot",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 10, "bold")
        ).pack(pady=3)

        # Link alternativo
        link_frame = tk.Frame(qr_frame, bg=COLORS["background"])
        link_frame.pack(pady=2)

        tk.Label(
            link_frame,
            text="Link directo: ",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 9)
        ).pack(side="left")

        link_label = tk.Label(
            link_frame,
            text="t.me/VingSecurityBot",
            bg=COLORS["background"],
            fg=COLORS["accent"],
            font=("Arial", 9, "underline"),
            cursor="hand2"
        )
        link_label.pack(side="left")
        link_label.bind("<Button-1>", lambda e: self._open_bot_link())

    def _create_qr_fallback(self, parent):
        qr_canvas = tk.Canvas(parent, width=120, height=120, bg="white", highlightthickness=0)
        qr_canvas.pack()

        # Dibujar patrón de QR simple
        qr_canvas.create_rectangle(25, 25, 45, 45, fill="black", outline="black")
        qr_canvas.create_rectangle(75, 25, 95, 45, fill="black", outline="black")
        qr_canvas.create_rectangle(25, 75, 45, 95, fill="black", outline="black")
        qr_canvas.create_rectangle(55, 55, 65, 65, fill="black", outline="black")

        tk.Label(
            parent.master,
            text="(Usar QR.ppm para código real)",
            bg=COLORS["background"],
            fg=COLORS["danger"],
            font=("Arial", 8)
        ).pack()

    def _create_instructions(self, parent):
        instructions_frame = tk.LabelFrame(
            parent,
            text="Instrucciones",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        instructions_frame.pack(fill="x", pady=(0, 10))

        instructions = [
            "1. Abre Telegram en tu celular",
            "2. Escanea el código QR",
            "3. Se abrirá @VingSecurityBot",
            "4. Envía un mensaje al bot:",
            "   - Para notificaciones: tu CORREO",
            "   - Para emergencias: 'EMERGENCIA tu_correo'",
            "5. Presiona el botón correspondiente",
            "6. Presiona 'Probar' para verificar"
        ]

        for instruction in instructions:
            tk.Label(
                instructions_frame,
                text=instruction,
                bg=COLORS["background"],
                fg=COLORS["text_dark"],
                font=("Arial", 9),
                justify="left"
            ).pack(anchor="w", pady=1)

    def _create_registration_buttons(self, parent):
        reg_frame = tk.LabelFrame(
            parent,
            text="Registro",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        reg_frame.pack(fill="x", pady=(0, 10))

        # Botón Registrarme (Notificaciones normales)
        self.btn_register = tk.Button(
            reg_frame,
            text="Registrarme para Notificaciones",
            bg=COLORS["secondary"],
            fg=COLORS["text_light"],
            font=("Arial", 10),
            width=28,
            height=1,
            command=self._register_user
        )
        self.btn_register.pack(pady=5)

        tk.Label(
            reg_frame,
            text="Envía tu CORREO al bot y presiona aquí",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 8)
        ).pack()

        # Separador
        tk.Frame(reg_frame, height=1, bg=COLORS["accent"]).pack(fill="x", pady=8, padx=20)

        # Botón Registrar Número de Emergencia
        self.btn_emergency = tk.Button(
            reg_frame,
            text="Registrar Número de Emergencia",
            bg=COLORS["danger"],
            fg=COLORS["text_light"],
            font=("Arial", 10),
            width=28,
            height=1,
            command=self._register_emergency
        )
        self.btn_emergency.pack(pady=5)

        tk.Label(
            reg_frame,
            text="Envía 'EMERGENCIA tu_correo' al bot y presiona aquí",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 8)
        ).pack()

        # Separador
        tk.Frame(reg_frame, height=1, bg=COLORS["accent"]).pack(fill="x", pady=8, padx=20)

        # Botón Actualizar Vinculaciones
        tk.Button(
            reg_frame,
            text="Actualizar Vinculaciones",
            bg=COLORS["accent"],
            fg=COLORS["text_light"],
            font=("Arial", 9),
            width=22,
            command=self._update_status
        ).pack(pady=5)

    def _create_test_buttons(self, parent):
        test_frame = tk.LabelFrame(
            parent,
            text="Pruebas",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        test_frame.pack(fill="x", pady=(0, 10))

        # Frame para botones en fila
        buttons_row = tk.Frame(test_frame, bg=COLORS["background"])
        buttons_row.pack()

        # Botón Probar Notificación
        self.btn_test = tk.Button(
            buttons_row,
            text="Probar Notificación",
            bg=COLORS["accent"],
            fg=COLORS["text_light"],
            font=("Arial", 9),
            width=18,
            command=self._test_notification
        )
        self.btn_test.pack(side="left", padx=5)

        # Botón Probar Notificación de Emergencia
        self.btn_test_emergency = tk.Button(
            buttons_row,
            text="Probar Emergencia",
            bg=COLORS["danger"],
            fg=COLORS["text_light"],
            font=("Arial", 9),
            width=18,
            command=self._test_emergency
        )
        self.btn_test_emergency.pack(side="left", padx=5)

        tk.Label(
            test_frame,
            text="Verifica que recibes los mensajes en Telegram",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 8)
        ).pack(pady=5)

    def _create_status_section(self, parent):
        status_frame = tk.LabelFrame(
            parent,
            text="Estado de Vinculación",
            bg=COLORS["background"],
            fg=COLORS["primary"],
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        status_frame.pack(fill="x")

        self.status_label = tk.Label(
            status_frame,
            text="Cargando estado...",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 9),
            justify="left",
            wraplength=250
        )
        self.status_label.pack(anchor="w", pady=3)

        self.emergency_label = tk.Label(
            status_frame,
            text="",
            bg=COLORS["background"],
            fg=COLORS["text_dark"],
            font=("Arial", 9),
            justify="left",
            wraplength=250
        )
        self.emergency_label.pack(anchor="w", pady=3)

    def _open_bot_link(self):
        try:
            webbrowser.open("https://t.me/VingSecurityBot")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el link: {e}")

    def _register_user(self):
        # Primero intentar con SecurityController si está disponible
        if self.security_controller:
            success, message, chat_id = self.security_controller.link_telegram_account(check_emergency=False)
            if success:
                messagebox.showinfo("Éxito", message)
                self._update_status()
                return
            else:
                # Si falla, mostrar instrucciones
                self._show_registration_instructions(check_emergency=False)
                return

        # Si no hay SecurityController, usar el método original
        if not self.telegram_bot:
            messagebox.showerror("Error", "Bot de Telegram no disponible")
            return

        if not self.current_user:
            messagebox.showerror("Error", "No hay usuario logueado")
            return

        # IMPORTANTE: Asegurar que el bot tenga el usuario actual
        self.telegram_bot.user_manager.current_user = self.current_user
        print(f"Usuario configurado en bot: {self.current_user}")

        # Mostrar instrucciones
        self._show_registration_instructions(check_emergency=False)

        # Buscar mensajes
        updated = self.telegram_bot.get_updates(check_emergency=False)

        if updated:
            messagebox.showinfo("Éxito",
                                f"Vinculación exitosa\n\n"
                                f"Usuario: {self.current_user}\n\n"
                                f"Ahora recibirás notificaciones de seguridad.\n\n"
                                f"Presiona 'Probar Notificación' para verificar.")
        else:
            username = self.current_user.split('@')[0] if '@' in self.current_user else self.current_user
            messagebox.showwarning(
                "No encontrado",
                f"No se encontró coincidencia.\n\n"
                f"Prueba enviando:\n"
                f"1. Tu correo completo: {self.current_user}\n"
                f"2. Solo tu nombre: {username}\n"
                f"3. Un mensaje que contenga tu correo\n\n"
                f"Luego presiona 'Actualizar Vinculaciones' y prueba de nuevo."
            )

        self._update_status()

    def _register_emergency(self):
        # Primero intentar con SecurityController si está disponible
        if self.security_controller:
            success, message, chat_id = self.security_controller.link_telegram_account(check_emergency=True)
            if success:
                messagebox.showinfo("Éxito", message)
                self._update_status()
                return
            else:
                # Si falla, mostrar instrucciones
                self._show_registration_instructions(check_emergency=True)
                return

        # Si no hay SecurityController, usar el método original
        if not self.telegram_bot:
            messagebox.showerror("Error", "Bot de Telegram no disponible")
            return

        if not self.current_user:
            messagebox.showerror("Error", "No hay usuario logueado")
            return

        # IMPORTANTE: Asegurar que el bot tenga el usuario actual
        self.telegram_bot.user_manager.current_user = self.current_user
        print(f"Usuario configurado en bot (emergencia): {self.current_user}")

        # Mostrar instrucciones
        self._show_registration_instructions(check_emergency=True)

        # Buscar mensajes
        updated = self.telegram_bot.get_updates(check_emergency=True)

        if updated:
            messagebox.showinfo("Éxito",
                                f"Emergencia registrada\n\n"
                                f"Usuario: {self.current_user}\n\n"
                                f"Recibirás alertas críticas del sistema.\n\n"
                                f"Presiona 'Probar Emergencia' para verificar.")
        else:
            username = self.current_user.split('@')[0] if '@' in self.current_user else self.current_user
            messagebox.showwarning(
                "No encontrado",
                f"No se encontró mensaje de emergencia.\n\n"
                f"Prueba enviando:\n"
                f"1. EMERGENCIA {self.current_user}\n"
                f"2. EMERGENCIA {username}\n"
                f"3. Cualquier mensaje con 'EMERGENCIA'\n\n"
                f"Luego presiona 'Actualizar Vinculaciones' y prueba de nuevo."
            )

        self._update_status()

    def _show_registration_instructions(self, check_emergency=False):
        """Muestra instrucciones para el registro"""
        username = self.current_user.split('@')[0] if '@' in self.current_user else self.current_user

        if check_emergency:
            title = "REGISTRO DE EMERGENCIA"
            instructions = f"Envía al bot (@VingSecurityBot) cualquiera de estos:\n\n" \
                           f"OPCION 1:\n" \
                           f"EMERGENCIA {self.current_user}\n\n" \
                           f"OPCION 2:\n" \
                           f"EMERGENCIA {username}\n\n" \
                           f"OPCION 3:\n" \
                           f"Cualquier mensaje con 'EMERGENCIA' y tu correo/nombre\n\n" \
                           f"Luego presiona OK para buscar."
        else:
            title = "CÓMO VINCULARSE"
            instructions = f"Envía al bot (@VingSecurityBot) cualquiera de estos mensajes:\n\n" \
                           f"OPCION 1 (recomendado):\n" \
                           f"{self.current_user}\n\n" \
                           f"OPCION 2:\n" \
                           f"{username}\n\n" \
                           f"OPCION 3:\n" \
                           f"Cualquier mensaje que contenga tu correo o nombre\n\n" \
                           f"Luego presiona OK para buscar."

        messagebox.showinfo(title, instructions)

    def _test_notification(self):
        # Intentar con SecurityController primero
        if self.security_controller:
            success, message = self.security_controller.send_test_notification(check_emergency=False)
            if success:
                messagebox.showinfo("Éxito", message)
            else:
                messagebox.showerror("Error", f"No se pudo enviar:\n{message}")
            return

        if not self.telegram_bot:
            messagebox.showerror("Error", "Bot de Telegram no disponible")
            return

        if not self.current_user:
            messagebox.showerror("Error", "No hay usuario logueado")
            return

        chat_id = self.telegram_bot.chat_ids.get(self.current_user)

        if not chat_id:
            messagebox.showwarning(
                "No vinculado",
                "No se encontró chat_id para tu usuario.\n"
                "Regístrate primero."
            )
            return

        success, result = self.telegram_bot.test_user_notification(self.current_user)

        if success:
            messagebox.showinfo("Éxito", "Notificación de prueba enviada.\nRevisa Telegram.")
        else:
            messagebox.showerror("Error", f"No se pudo enviar:\n{result}")

    def _test_emergency(self):
        # Intentar con SecurityController primero
        if self.security_controller:
            success, message = self.security_controller.send_test_notification(check_emergency=True)
            if success:
                messagebox.showinfo("Éxito", message)
            else:
                messagebox.showerror("Error", f"No se pudo enviar:\n{message}")
            return


        if not self.telegram_bot:
            messagebox.showerror("Error", "Bot de Telegram no disponible")
            return

        if not self.current_user:
            messagebox.showerror("Error", "No hay usuario logueado")
            return

        emergency_chat_id = self.telegram_bot.emergency_chat_ids.get(self.current_user)

        if not emergency_chat_id:
            messagebox.showwarning(
                "No configurado",
                "No se encontró número de emergencia.\n"
                "Registra emergencia primero."
            )
            return

        success, result = self.telegram_bot.test_emergency_notification(self.current_user)

        if success:
            messagebox.showinfo("Éxito", "Notificación de emergencia enviada.\nRevisa Telegram.")
        else:
            messagebox.showerror("Error", f"No se pudo enviar:\n{result}")

    def _update_status(self):
        if not self.current_user:
            self.status_label.config(text="No hay usuario logueado", fg=COLORS["danger"])
            self.emergency_label.config(text="")
            return

        profile = self.user_manager.get_current_user_profile()

        if not profile:
            self.status_label.config(text="No se pudo obtener perfil", fg=COLORS["danger"])
            self.emergency_label.config(text="")
            return

        # Usar SecurityController si está disponible
        if self.security_controller:
            status_info = self.security_controller.get_telegram_status()

            if status_info['telegram_linked']:
                self.status_label.config(
                    text=f" Vinculado para notificaciones\nChat ID: {status_info['chat_id']}",
                    fg=COLORS["accent"]
                )
            else:
                self.status_label.config(
                    text=" No vinculado para notificaciones\n(Escanear QR y enviar correo)",
                    fg=COLORS["danger"]
                )

            if status_info['emergency_linked']:
                self.emergency_label.config(
                    text=f" Emergencia configurada\nChat ID: {status_info['emergency_chat_id']}",
                    fg=COLORS["danger"]
                )
            else:
                self.emergency_label.config(
                    text=" No configurado para emergencias\n(Escanear QR y enviar 'EMERGENCIA')",
                    fg=COLORS["text_dark"]
                )
        else:
            chat_id = profile.get('chat_id')
            telegram_linked = profile.get('telegram_linked', False)

            if telegram_linked and chat_id:
                self.status_label.config(
                    text=f"Vinculado para notificaciones\nChat ID: {chat_id}",
                    fg=COLORS["accent"]
                )
            else:
                self.status_label.config(
                    text="No vinculado para notificaciones\n(Escanear QR y enviar correo)",
                    fg=COLORS["danger"]
                )

            emergency_chat_id = profile.get('emergency_chat_id')
            emergency_linked = profile.get('emergency_linked', False)

            if emergency_linked and emergency_chat_id:
                self.emergency_label.config(
                    text=f"Emergencia configurada\nChat ID: {emergency_chat_id}",
                    fg=COLORS["danger"]
                )
            else:
                self.emergency_label.config(
                    text="No configurado para emergencias\n(Escanear QR y enviar 'EMERGENCIA')",
                    fg=COLORS["text_dark"]
                )
