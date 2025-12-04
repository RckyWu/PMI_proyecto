"""
Modelo de gestión de usuarios
Maneja registro, login y persistencia en JSON
"""

import json
import os
import hashlib
from pathlib import Path


class UserManager:
    """Gestiona usuarios y autenticación"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        self.user_data_dir = self.data_dir / "user_data"
        
        # Crear directorios si no existen
        self.data_dir.mkdir(exist_ok=True)
        self.user_data_dir.mkdir(exist_ok=True)
        
        self.users = self._load_users()
        self.current_user = None
    
    def _load_users(self):
        """Carga el índice de usuarios desde el archivo JSON"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_users(self):
        """Guarda el índice de usuarios en el archivo JSON"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=4, ensure_ascii=False)
    
    def _hash_password(self, password):
        """Hashea la contraseña para seguridad"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _get_user_dir(self, email):
        """Retorna el directorio del usuario"""
        # Sanitizar el email para usarlo como nombre de carpeta
        safe_email = email.replace('@', '_at_').replace('.', '_')
        return self.user_data_dir / safe_email
    
    def _create_user_directory(self, email, telegram):
        """Crea el directorio y archivos iniciales del usuario"""
        user_dir = self._get_user_dir(email)
        user_dir.mkdir(exist_ok=True)
        
        # Crear profile.json
        profile_data = {
            "email": email,
            "telegram": telegram,
            "created_at": None  # Puedes agregar timestamp si quieres
        }
        profile_file = user_dir / "profile.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=4, ensure_ascii=False)
        
        # Crear devices.json vacío
        devices_file = user_dir / "devices.json"
        with open(devices_file, 'w', encoding='utf-8') as f:
            json.dump({"devices_by_zone": {}}, f, indent=4, ensure_ascii=False)
    
    def register(self, email, password, telegram):
        """
        Registra un nuevo usuario
        Returns: (success: bool, message: str)
        """
        if email in self.users:
            return False, "El correo ya está registrado"
        
        # Validar contraseña
        if len(password) < 4:
            return False, "La contraseña debe tener mínimo 4 caracteres"
        if not any(c.isupper() for c in password):
            return False, "La contraseña debe tener al menos 1 mayúscula"
        if not any(c.isdigit() for c in password):
            return False, "La contraseña debe tener al menos 1 número"
        
        # Guardar credenciales en users.json
        self.users[email] = {
            "password": self._hash_password(password)
        }
        self._save_users()
        
        # Crear carpeta y archivos del usuario
        self._create_user_directory(email, telegram)
        
        return True, "Usuario registrado exitosamente"
    
    def login(self, email, password):
        """
        Intenta hacer login
        Returns: (success: bool, message: str)
        """
        if email not in self.users:
            return False, "Usuario no encontrado"
        
        hashed = self._hash_password(password)
        if self.users[email]["password"] == hashed:
            self.current_user = email
            return True, "Login exitoso"
        else:
            return False, "Contraseña incorrecta"
    
    def logout(self):
        """Cierra sesión del usuario actual"""
        self.current_user = None
    
    def get_current_user_profile(self):
        """Retorna el perfil completo del usuario actual"""
        if not self.current_user:
            return None
        
        user_dir = self._get_user_dir(self.current_user)
        profile_file = user_dir / "profile.json"
        
        if profile_file.exists():
            with open(profile_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_user_devices_file(self):
        """Retorna la ruta del archivo de dispositivos del usuario actual"""
        if not self.current_user:
            return None
        
        user_dir = self._get_user_dir(self.current_user)
        return user_dir / "devices.json"    