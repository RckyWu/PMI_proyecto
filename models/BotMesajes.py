import requests
import json
import time
import os
from pathlib import Path
from user_manager import UserManager


class TelegramBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.user_manager = UserManager()
        self.chat_ids = self._load_chat_ids()
        self.user_profiles = self._find_all_profiles()
        self.newly_linked_users = []  # Para trackear usuarios recién vinculados

    def _find_all_profiles(self):
        """Busca automáticamente todos los archivos profile.json en el sistema"""
        print(" Buscando perfiles de usuario...")
        profiles = {}

        # Ruta específica donde encontramos los perfiles
        user_data_path = Path("../data/user_data")

        if user_data_path.exists():
            print(f"    Buscando en: {user_data_path.absolute()}")
            for profile_file in user_data_path.rglob("profile.json"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        profile_data = json.load(f)

                    email = profile_data.get('email')
                    if email:
                        profiles[email] = {
                            'data': profile_data,
                            'file_path': profile_file,
                            'telegram': profile_data.get('telegram', '')
                        }
                        print(f"    Encontrado: {email} -> Telegram: '{profile_data.get('telegram')}'")
                except Exception as e:
                    print(f"    Error leyendo {profile_file}: {e}")
        else:
            print(f"    No se encontró la ruta: {user_data_path}")

        print(f"    Total de perfiles encontrados: {len(profiles)}")
        return profiles

    def _load_chat_ids(self):
        """Carga los IDs de chat guardados para cada usuario"""
        chat_ids_file = Path("chat_ids.json")
        if chat_ids_file.exists():
            try:
                with open(chat_ids_file, 'r', encoding='utf-8') as f:
                    print(f"✅ Cargando chat_ids desde: {chat_ids_file}")
                    return json.load(f)
            except Exception as e:
                print(f"❌ Error cargando chat_ids: {e}")

        print("️ No se encontró archivo chat_ids.json, creando uno nuevo")
        return {}

    def _save_chat_ids(self):
        """Guarda los IDs de chat en un archivo JSON"""
        chat_ids_file = Path("chat_ids.json")
        with open(chat_ids_file, 'w', encoding='utf-8') as f:
            json.dump(self.chat_ids, f, indent=4, ensure_ascii=False)
        print(f" Chat_ids guardados en: {chat_ids_file}")

    def get_updates(self):
        """Obtiene las actualizaciones recientes del bot y actualiza los IDs de chat"""
        url = f"{self.base_url}/getUpdates"

        try:
            response = requests.get(url)
            data = response.json()

            if data['ok'] and data['result']:
                updated = False
                for update in data['result']:
                    if 'message' in update:
                        chat_id = str(update['message']['chat']['id'])
                        user_name = update['message']['chat'].get('first_name', 'Usuario')
                        username = update['message']['chat'].get('username', '')

                        print(f"\n📱 Mensaje de: {user_name} (@{username}) - Chat ID: {chat_id}")

                        # Buscar usuario por nombre de Telegram y guardar chat_id
                        user_found = self._find_and_save_user_chat_id(user_name, username, chat_id)
                        if user_found:
                            updated = True

                if updated:
                    self._save_chat_ids()
                    # Enviar mensajes de bienvenida a los nuevos usuarios vinculados
                    self._send_welcome_messages()

                return True
            else:
                print(" No hay mensajes recientes")
                return False

        except Exception as e:
            print(f" Error obteniendo updates: {e}")
            return False

    def _find_and_save_user_chat_id(self, first_name, username, chat_id):
        """Busca usuario por nombre de Telegram y guarda su chat_id"""
        print(f"🔍 Buscando perfil para: '{first_name}' (@{username})")

        if not self.user_profiles:
            print(" No hay perfiles de usuario disponibles")
            return False

        for email, profile_info in self.user_profiles.items():
            telegram_field = profile_info['telegram']
            profile_data = profile_info['data']

            if not telegram_field:
                continue

            print(f"    Comparando con: {email} -> '{telegram_field}'")

            # Limpiar strings para comparación
            telegram_clean = str(telegram_field).lower().strip()
            first_name_clean = str(first_name).lower().strip()
            username_clean = str(username).lower().strip() if username else ""

            # Verificar diferentes tipos de coincidencia
            matches = []

            # Coincidencia exacta (caso de Ronald)
            if telegram_clean == first_name_clean:
                matches.append("coincidencia exacta con first_name")

            # Coincidencia con username
            if username_clean and telegram_clean == username_clean:
                matches.append("coincidencia exacta con username")

            # Coincidencia parcial - Ronald en cualquier parte
            if first_name_clean in telegram_clean:
                matches.append("first_name contenido en campo telegram")

            if telegram_clean in first_name_clean:
                matches.append("campo telegram contenido en first_name")

            # Coincidencia numérica (para los otros usuarios)
            if telegram_field.isdigit() and username_clean.isdigit() and telegram_field == username_clean:
                matches.append("coincidencia numérica con username")

            # Coincidencia más flexible - cualquier parte común
            common_chars = set(first_name_clean) & set(telegram_clean)
            if len(common_chars) >= 3:  # Si tienen al menos 3 caracteres en común
                matches.append("coincidencia por caracteres comunes")

            # Si encontramos coincidencias
            if matches:
                print(f"    COINCIDENCIA ENCONTRADA: {', '.join(matches)}")

                # Verificar si es una nueva vinculación
                is_new_link = email not in self.chat_ids
                old_chat_id = self.chat_ids.get(email)

                # Guardar el chat_id
                self.chat_ids[email] = chat_id
                print(f"    Chat ID {chat_id} asignado a: {email}")

                # Actualizar el perfil
                self._update_user_profile(email, chat_id, profile_info['file_path'])

                # Si es una nueva vinculación, agregar a la lista para enviar mensaje
                if is_new_link:
                    self.newly_linked_users.append({
                        'email': email,
                        'chat_id': chat_id,
                        'first_name': first_name,
                        'telegram_name': telegram_field
                    })
                    print(f"    Nuevo usuario vinculado: {email}")
                elif old_chat_id != chat_id:
                    print(f"    Chat ID actualizado para: {email}")

                return True

        print(f"    No se encontró coincidencia para '{first_name}'")
        print(f"    Perfiles disponibles: {list(self.user_profiles.keys())}")
        return False

    def _send_welcome_messages(self):
        """Envía mensajes de bienvenida a los usuarios recién vinculados"""
        if not self.newly_linked_users:
            return

        print(f"\n🎉 Enviando mensajes de bienvenida a {len(self.newly_linked_users)} usuarios...")

        for user_info in self.newly_linked_users:
            email = user_info['email']
            chat_id = user_info['chat_id']
            first_name = user_info['first_name']
            telegram_name = user_info['telegram_name']

            welcome_message = f"""
 <b>¡Vinculación Exitosa!</b>

¡Hola <b>{first_name}</b>! 

Tu cuenta de Telegram ha sido vinculada exitosamente con el sistema de seguridad.

<b>Email asociado:</b> {email}
 <b>Nombre en Telegram:</b> {telegram_name}
 <b>Chat ID:</b> <code>{chat_id}</code>

 <b>Ahora recibirás:</b>
• Alertas de seguridad en tiempo real
• Notificaciones de estado del sistema
• Recordatorios importantes

 <i>Este chat está destinado exclusivamente para alertas del sistema de seguridad.</i>

Si tienes alguna pregunta, contacta al administrador del sistema.

Saludos,
Sistema de Seguridad Ving 
            """.strip()

            success, result = self.send_message(chat_id, welcome_message)

            if success:
                print(f"    Mensaje de bienvenida enviado a: {first_name} ({email})")
            else:
                print(f"    Error enviando mensaje a {email}: {result}")

        # Limpiar la lista después de enviar los mensajes
        self.newly_linked_users.clear()

    def _update_user_profile(self, email, chat_id, profile_path):
        """Actualiza el perfil del usuario con el chat_id"""
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            profile['chat_id'] = chat_id
            profile['telegram_linked'] = True
            profile['telegram_linked_at'] = time.strftime("%Y-%m-%d %H:%M:%S")

            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=4, ensure_ascii=False)

            print(f"   Perfil actualizado: {email}")

        except Exception as e:
            print(f" Error actualizando perfil {profile_path}: {e}")

    def send_message(self, chat_id, text, parse_mode='HTML'):
        """Envía un mensaje de texto"""
        url = f"{self.base_url}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result['ok'], result.get('result', {})

        except requests.exceptions.RequestException as e:
            return False, f"Error de conexión: {e}"
        except Exception as e:
            return False, f"Error: {e}"

    def send_message_to_user(self, email, text, parse_mode='HTML'):
        """Envía mensaje a un usuario específico por email"""
        chat_id = self.chat_ids.get(email)
        if chat_id:
            return self.send_message(chat_id, text, parse_mode)
        else:
            return False, f"No se encontró chat_id para: {email}"

    def list_linked_users(self):
        """Lista todos los usuarios vinculados con sus chat_ids"""
        print("\n USUARIOS VINCULADOS CON TELEGRAM:")
        print("=" * 50)

        if not self.chat_ids:
            print("No hay usuarios vinculados")
            return

        for email, chat_id in self.chat_ids.items():
            telegram_name = self.user_profiles.get(email, {}).get('telegram', 'Desconocido')
            profile_linked = self.user_profiles.get(email, {}).get('data', {}).get('telegram_linked', False)
            status = " Activo" if profile_linked else "No verificado"

            print(f" {email}")
            print(f"    Telegram: {telegram_name}")
            print(f"    Chat ID: {chat_id}")
            print(f"    Estado: {status}")
            print()

    def force_link_user(self, email, chat_id, send_welcome=True):
        """Fuerza la vinculación de un usuario manualmente"""
        # Verificar si es una nueva vinculación
        is_new_link = email not in self.chat_ids

        self.chat_ids[email] = chat_id
        self._save_chat_ids()

        # También actualizar el perfil si existe
        if email in self.user_profiles:
            profile_info = self.user_profiles[email]
            self._update_user_profile(email, chat_id, profile_info['file_path'])

            # Si es nueva vinculación y se solicita enviar welcome
            if is_new_link and send_welcome:
                user_info = {
                    'email': email,
                    'chat_id': chat_id,
                    'first_name': profile_info['data'].get('telegram', 'Usuario'),
                    'telegram_name': profile_info['telegram']
                }
                self.newly_linked_users.append(user_info)
                self._send_welcome_messages()

        print(f" Vinculación manual: {email} -> {chat_id}")

    def get_me(self):
        """Obtiene información del bot"""
        url = f"{self.base_url}/getMe"
        response = requests.get(url)
        return response.json()

    def send_test_message(self, email):
        """Envía un mensaje de prueba a un usuario"""
        test_message = """
 <b>Mensaje de Prueba</b>

¡Hola! Este es un mensaje de prueba del sistema de seguridad.

 Si recibes este mensaje, significa que tu vinculación con Telegram está funcionando correctamente.

 A partir de ahora recibirás alertas importantes del sistema.

Saludos,
Sistema de Seguridad Ving 
        """.strip()

        return self.send_message_to_user(email, test_message)



if __name__ == "__main__":
    BOT_TOKEN = "8587676832:AAHx9szhD1mjCJXzlHHN81aR90aPh3j7w-I"

    bot = TelegramBot(BOT_TOKEN)

    # Verificar conexión
    bot_info = bot.get_me()
    if bot_info['ok']:
        bot_name = bot_info['result']['first_name']
        print(f" Bot conectado: {bot_name}")
    else:
        print(" Error conectando con el bot")
        exit()

    # Obtener actualizaciones
    print("\n Buscando actualizaciones...")
    bot.get_updates()

    # Mostrar resultados
    bot.list_linked_users()