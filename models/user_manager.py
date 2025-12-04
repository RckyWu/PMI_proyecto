"""
Modelo de gestion de usuarios
Maneja registro, login y persistencia en JSON
"""

import json
import hashlib
from pathlib import Path
import os


class UserManager:

    def __init__(self, data_dir="data"):
        # Usar ruta absoluta desde el directorio del proyecto
        current_dir = Path(__file__).parent.parent  # Ir a raíz del proyecto
        self.data_dir = current_dir / data_dir
        self.users_file = self.data_dir / "users.json"
        self.user_data_dir = self.data_dir / "user_data"

        print(f"Directorio de datos: {self.data_dir.absolute()}")
        print(f"Directorio de usuarios: {self.user_data_dir.absolute()}")

        # Crear directorios si no existen
        self.data_dir.mkdir(exist_ok=True)
        self.user_data_dir.mkdir(exist_ok=True)

        self.users = self._load_users()
        self.current_user = None

    def _load_users(self):
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=4, ensure_ascii=False)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def _get_user_dir(self, email):
        safe_email = email.replace('@', '_at_').replace('.', '_')
        return self.user_data_dir / safe_email

    def _create_user_directory(self, email, telegram):
        user_dir = self._get_user_dir(email)
        user_dir.mkdir(exist_ok=True)

        profile_data = {
            "email": email,
            "telegram": telegram,
            "telegram_linked": False,
            "emergency_linked": False,
            "created_at": None
        }
        profile_file = user_dir / "profile.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=4, ensure_ascii=False)

        devices_file = user_dir / "devices.json"
        with open(devices_file, 'w', encoding='utf-8') as f:
            json.dump({"devices_by_zone": {}}, f, indent=4, ensure_ascii=False)

    def register(self, email, password, telegram):
        if email in self.users:
            return False, "El correo ya esta registrado"

        if len(password) < 4:
            return False, "La contraseña debe tener minimo 4 caracteres"
        if not any(c.isupper() for c in password):
            return False, "La contraseña debe tener al menos 1 mayuscula"
        if not any(c.isdigit() for c in password):
            return False, "La contraseña debe tener al menos 1 numero"

        self.users[email] = {
            "password": self._hash_password(password)
        }
        self._save_users()

        self._create_user_directory(email, telegram)

        return True, "Usuario registrado exitosamente"

    def login(self, email, password):
        if email not in self.users:
            return False, "Usuario no encontrado"

        hashed = self._hash_password(password)
        if self.users[email]["password"] == hashed:
            self.current_user = email
            return True, "Login exitoso"
        else:
            return False, "Contraseña incorrecta"

    def logout(self):
        self.current_user = None

    def get_current_user_profile(self):
        if not self.current_user:
            return None

        user_dir = self._get_user_dir(self.current_user)
        profile_file = user_dir / "profile.json"

        if profile_file.exists():
            with open(profile_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_user_devices_file(self):
        if not self.current_user:
            return None

        user_dir = self._get_user_dir(self.current_user)
        return user_dir / "devices.json"

    def update_user_profile(self, email, updates):
        user_dir = self._get_user_dir(email)
        profile_file = user_dir / "profile.json"

        if profile_file.exists():
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)

                profile.update(updates)

                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(profile, f, indent=4, ensure_ascii=False)

                return True
            except Exception as e:
                print(f"Error actualizando perfil {email}: {e}")
                return False
        return False

    def get_user_chat_id(self, email):
        """Obtiene el chat_id de un usuario desde su perfil"""
        profile = self.get_current_user_profile() if email == self.current_user else None
        return profile.get('chat_id') if profile else None

    def get_user_emergency_chat_id(self, email):
        """Obtiene el chat_id de emergencia de un usuario"""
        profile = self.get_current_user_profile() if email == self.current_user else None
        return profile.get('emergency_chat_id') if profile else None