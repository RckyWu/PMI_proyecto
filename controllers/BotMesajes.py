import requests
import json
import time
import re
from pathlib import Path
from models.user_manager import UserManager


class TelegramBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.user_manager = UserManager()  # UserManager vacío al inicio
        self.chat_ids = self._load_chat_ids()
        self.emergency_chat_ids = self._load_emergency_chat_ids()

        print(f"Bot inicializado. Token: {bot_token[:10]}...")
        print(f"UserManager configurado. Current user inicial: {self.user_manager.current_user}")

    def _load_chat_ids(self):
        chat_ids_file = Path("chat_ids.json")
        if chat_ids_file.exists():
            try:
                with open(chat_ids_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"Chat IDs cargados del archivo: {data}")
                    return data
            except Exception as e:
                print(f"Error cargando chat_ids: {e}")

        print("Creando chat_ids.json nuevo")
        return {}

    def _load_emergency_chat_ids(self):
        emergency_file = Path("emergency_chat_ids.json")
        if emergency_file.exists():
            try:
                with open(emergency_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error cargando emergency_chat_ids: {e}")

        print("Creando emergency_chat_ids.json nuevo")
        return {}

    def _save_chat_ids(self):
        chat_ids_file = Path("chat_ids.json")
        with open(chat_ids_file, 'w', encoding='utf-8') as f:
            json.dump(self.chat_ids, f, indent=4, ensure_ascii=False)
        print(f"Chat IDs guardados: {self.chat_ids}")

    def _save_emergency_chat_ids(self):
        emergency_file = Path("emergency_chat_ids.json")
        with open(emergency_file, 'w', encoding='utf-8') as f:
            json.dump(self.emergency_chat_ids, f, indent=4, ensure_ascii=False)
        print(f"Emergency Chat IDs guardados: {self.emergency_chat_ids}")

    def get_updates(self, check_emergency=False):
        """Busca mensajes recientes del bot - VERSION CORREGIDA"""
        url = f"{self.base_url}/getUpdates"

        # VERIFICAR USUARIO ACTUAL ANTES DE PROCESAR
        current_user = self.user_manager.current_user
        if not current_user:
            print(" ERROR CRITICO: No hay usuario logueado en UserManager")
            print(f"   UserManager.current_user = {self.user_manager.current_user}")
            print(f"   ¿Se configuró el usuario desde la interfaz?")
            return False

        print(f" Usuario actual configurado: {current_user}")

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if data['ok'] and data['result']:
                print(f"\n=== ANALIZANDO {len(data['result'])} MENSAJES PARA {current_user} ===")
                found = False

                for update in data['result']:
                    if 'message' in update:
                        chat_id = str(update['message']['chat']['id'])
                        user_name = update['message']['chat'].get('first_name', 'Usuario')
                        message_text = update['message'].get('text', '').strip()

                        print(f"\nMensaje #{data['result'].index(update) + 1}:")
                        print(f"  De: {user_name}")
                        print(f"  Chat ID: {chat_id}")
                        print(f"  Texto: '{message_text}'")

                        if check_emergency:
                            # Buscar mensaje de emergencia
                            if self._process_emergency_message(chat_id, message_text, user_name, current_user):
                                found = True
                        else:
                            # Buscar mensaje normal
                            if self._process_normal_message(chat_id, message_text, user_name, current_user):
                                found = True

                print(f"\n=== RESULTADO PARA {current_user}: {' ENCONTRADO' if found else ' NO ENCONTRADO'} ===")

                if found:
                    if check_emergency:
                        self._save_emergency_chat_ids()
                    else:
                        self._save_chat_ids()

                return found
            else:
                print(" No hay mensajes nuevos en el historial")
                return False

        except Exception as e:
            print(f" Error obteniendo updates: {e}")
            return False

    def _process_normal_message(self, chat_id, message_text, sender_name, current_user):
        """Procesa mensaje normal - RECIBE current_user COMO PARAMETRO"""

        print(f"  Buscando coincidencias para usuario: {current_user}")
        print(f"  Nombre del remitente en Telegram: {sender_name}")

        # Limpiar textos
        message_clean = message_text.lower().strip()
        user_email_lower = current_user.lower()

        # Extraer nombre de usuario del correo (parte antes del @)
        username_from_email = current_user.split('@')[0].lower() if '@' in current_user else ""

        print(f"  Usuario de correo: '{username_from_email}'")
        print(f"  Mensaje: '{message_clean}'")

        # CRITERIOS DE COINCIDENCIA
        coincidencias = []

        # 1. Coincidencia exacta de correo
        if user_email_lower == message_clean:
            coincidencias.append("CORREO EXACTO")

        # 2. Correo contenido en el mensaje
        if user_email_lower in message_clean:
            coincidencias.append("CORREO EN MENSAJE")

        # 3. Nombre de usuario (parte antes del @) en el mensaje
        if username_from_email and username_from_email in message_clean:
            coincidencias.append(f"NOMBRE '{username_from_email}' EN MENSAJE")

        # 4. Nombre del remitente coincide con nombre de usuario
        if username_from_email and sender_name.lower() == username_from_email:
            coincidencias.append(f"NOMBRE REMITENTE IGUAL A '{username_from_email}'")

        # 5. Parte del nombre del remitente en el correo
        if sender_name.lower() in user_email_lower:
            coincidencias.append(f"NOMBRE '{sender_name}' EN CORREO")

        # 6. Coincidencia parcial (primeras 3 letras)
        if username_from_email and sender_name.lower() and username_from_email[:3] == sender_name.lower()[:3]:
            coincidencias.append(f"PRIMERAS 3 LETRAS COINCIDEN")

        # Si hay alguna coincidencia
        if coincidencias:
            print(f"   COINCIDENCIAS ENCONTRADAS:")
            for i, coin in enumerate(coincidencias, 1):
                print(f"     {i}. {coin}")

            print(f"  Asignando Chat ID {chat_id} a {current_user}")

            # Guardar chat_id
            self.chat_ids[current_user] = chat_id

            # Actualizar perfil
            self._update_user_profile(current_user, chat_id, "normal")

            # Enviar confirmacion
            self._send_confirmation_message(chat_id, current_user, "normal", sender_name)

            return True
        else:
            print(f"   NO COINCIDE")
            print(f"    ¿Buscaste correctamente?")
            print(f"    Correo: '{user_email_lower}'")
            print(f"    Usuario: '{username_from_email}'")
            print(f"    Remitente Telegram: '{sender_name.lower()}'")
            return False

    def _process_emergency_message(self, chat_id, message_text, sender_name, current_user):
        """Procesa mensaje de emergencia - RECIBE current_user COMO PARAMETRO"""

        print(f"  Buscando EMERGENCIA para: {current_user}")

        message_lower = message_text.lower().strip()
        user_email_lower = current_user.lower()
        username_from_email = current_user.split('@')[0].lower() if '@' in current_user else ""

        # Verificar si es mensaje de emergencia
        es_emergencia = ("emergencia" in message_lower or "emergency" in message_lower)

        if not es_emergencia:
            print("   No es mensaje de emergencia")
            return False

        print(f"   Es mensaje de emergencia")
        print(f"  Buscando '{current_user}' o '{username_from_email}' en el mensaje")

        # CRITERIOS para emergencia
        coincidencias = []

        # 1. Correo en mensaje de emergencia
        if user_email_lower in message_lower:
            coincidencias.append("CORREO EN EMERGENCIA")

        # 2. Nombre de usuario en emergencia
        if username_from_email and username_from_email in message_lower:
            coincidencias.append(f"NOMBRE '{username_from_email}' EN EMERGENCIA")

        # 3. Nombre del remitente
        if sender_name.lower() == username_from_email:
            coincidencias.append(f"REMITENTE '{sender_name}' COINCIDE")

        if coincidencias:
            print(f"   EMERGENCIA ENCONTRADA:")
            for i, coin in enumerate(coincidencias, 1):
                print(f"     {i}. {coin}")

            print(f"  Registrando Chat ID {chat_id} como emergencia para {current_user}")

            # Guardar como emergencia
            self.emergency_chat_ids[current_user] = chat_id

            # Actualizar perfil
            self._update_user_profile(current_user, chat_id, "emergency")

            # Enviar confirmacion
            self._send_confirmation_message(chat_id, current_user, "emergency", sender_name)

            return True
        else:
            print(f"   EMERGENCIA NO COINCIDE")
            print(f"    Mensaje de emergencia debe contener tu correo o nombre")
            return False

    def _update_user_profile(self, email, chat_id, contact_type):
        """Actualiza el perfil del usuario"""
        try:
            user_dir = self.user_manager._get_user_dir(email)
            profile_file = user_dir / "profile.json"

            if not profile_file.exists():
                print(f"  ️ Creando perfil nuevo para {email}")
                # Crear perfil si no existe
                profile_data = {
                    "email": email,
                    "telegram_linked": False,
                    "emergency_linked": False,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)

            if contact_type == "normal":
                profile_data['chat_id'] = chat_id
                profile_data['telegram_linked'] = True
                profile_data['telegram_linked_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  Perfil NORMAL actualizado para {email}")
            elif contact_type == "emergency":
                profile_data['emergency_chat_id'] = chat_id
                profile_data['emergency_linked'] = True
                profile_data['emergency_linked_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  Perfil EMERGENCIA actualizado para {email}")

            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=4, ensure_ascii=False)

            print(f"  Perfil guardado en: {profile_file}")

        except Exception as e:
            print(f"   ERROR actualizando perfil {email}: {e}")

    def _send_confirmation_message(self, chat_id, email, message_type, sender_name):
        """Envia mensaje de confirmacion por Telegram"""
        if message_type == "normal":
            message = f"VINCULACION EXITOSA\n\nHola {sender_name},\n\nTu cuenta {email} ha sido vinculada con el sistema de seguridad Ving.\n\nAhora recibiras notificaciones de seguridad.\n\nID de Chat: {chat_id}"
        else:
            message = f"EMERGENCIA REGISTRADA\n\nHola {sender_name},\n\nTu numero ha sido registrado como contacto de emergencia para {email}.\n\nRecibiras alertas criticas del sistema.\n\nID de Chat: {chat_id}"

        print(f"  Enviando confirmacion a Chat ID {chat_id}")
        success, result = self.send_message(chat_id, message)

        if success:
            print(f"   Confirmacion enviada a Telegram")
        else:
            print(f"   Error enviando confirmacion: {result}")

    def send_message(self, chat_id, text, parse_mode='HTML'):
        url = f"{self.base_url}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result['ok'], result.get('result', {})

        except requests.exceptions.RequestException as e:
            return False, f"Error de conexion: {e}"
        except Exception as e:
            return False, f"Error: {e}"

    def send_message_to_user(self, email, text, parse_mode='HTML'):
        chat_id = self.chat_ids.get(email)
        if chat_id:
            return self.send_message(chat_id, text, parse_mode)
        else:
            return False, f"No hay chat_id para {email}"

    def send_emergency_message(self, email, text, parse_mode='HTML'):
        chat_id = self.emergency_chat_ids.get(email)
        if chat_id:
            return self.send_message(chat_id, text, parse_mode)
        else:
            return False, f"No hay chat_id de emergencia para {email}"

    # --- MÉTODOS DE PRUEBA  ---
    def test_user_notification(self, email):
        """Envia mensaje de prueba"""
        test_message = f"""
 PRUEBA DE NOTIFICACION

Hola,

Este es un mensaje de prueba del sistema de seguridad Ving.

 Tu vinculacion con Telegram esta funcionando correctamente.

Ahora recibiras alertas de seguridad en tiempo real.

 Usuario: {email}

Saludos,
Sistema de Seguridad Ving
        """.strip()

        return self.send_message_to_user(email, test_message)

    def test_emergency_notification(self, email):
        """Envia mensaje de prueba de emergencia"""
        emergency_message = f"""
PRUEBA DE EMERGENCIA

ALERTA DE PRUEBA

Este es un mensaje de prueba de emergencia del sistema de seguridad Ving.

Tu numero de emergencia esta configurado correctamente.

En caso de activacion del boton de panico, recibiras alertas similares.

Usuario: {email}

Saludos,
Sistema de Seguridad Ving
        """.strip()

        return self.send_emergency_message(email, emergency_message)

    def get_me(self):
        url = f"{self.base_url}/getMe"
        try:
            response = requests.get(url, timeout=10)
            return response.json()
        except:
            return {'ok': False}