import contextlib
import requests
import json
import time
from models.user_manager import UserManager  # ← CORREGIDO: Importar desde models


class TelegramBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.user_manager = UserManager()
        self.chat_ids = self._load_chat_ids()

    def _load_chat_ids(self):
        """Carga los IDs de chat guardados para cada usuario"""
        chat_ids_file = self.user_manager.data_dir / "chat_ids.json"
        if chat_ids_file.exists():
            try:
                with open(chat_ids_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_chat_ids(self):
        """Guarda los IDs de chat en un archivo JSON"""
        chat_ids_file = self.user_manager.data_dir / "chat_ids.json"
        with open(chat_ids_file, 'w', encoding='utf-8') as f:
            json.dump(self.chat_ids, f, indent=4, ensure_ascii=False)

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

                        print(f"Chat ID: {chat_id} - Usuario: {user_name} (@{username})")

                        # Buscar usuario por nombre de Telegram y guardar chat_id
                        user_found = self._find_and_save_user_chat_id(user_name, username, chat_id)
                        if user_found:
                            updated = True

                if updated:
                    self._save_chat_ids()

                return True
            else:
                print("No hay mensajes recientes. Envía un mensaje al bot primero.")
                return False

        except Exception as e:
            print(f"Error obteniendo updates: {e}")
            return False

    def _find_and_save_user_chat_id(self, first_name, username, chat_id):
        """Busca usuario por nombre de Telegram y guarda su chat_id"""
        # Buscar en todos los perfiles de usuario
        users_data = {}
        users_file = self.user_manager.data_dir / "users.json"

        if users_file.exists():
            with contextlib.suppress(Exception):
                with open(users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
        # Buscar en los directorios de usuarios
        user_dirs = [d for d in self.user_manager.user_data_dir.iterdir() if d.is_dir()]

        for user_dir in user_dirs:
            profile_file = user_dir / "profile.json"
            if profile_file.exists():
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        profile = json.load(f)

                    telegram_field = profile.get('telegram', '').lower()
                    user_email = profile.get('email', '')

                    # Comparar con diferentes formatos del campo telegram
                    search_terms = [
                        first_name.lower(),
                        username.lower() if username else '',
                        f"@{username.lower()}" if username else ''
                    ]

                    for term in search_terms:
                        if term and term in telegram_field:
                            # Guardar el chat_id para este usuario
                            self.chat_ids[user_email] = chat_id
                            print(f"✅ Chat ID {chat_id} asignado a usuario: {user_email}")

                            # Actualizar también el perfil del usuario
                            self._update_user_profile_chat_id(user_email, chat_id)
                            return True

                except Exception as e:
                    print(f"Error procesando perfil {user_dir}: {e}")

        print(f"⚠️ Usuario de Telegram '{first_name}' (@{username}) no encontrado en la base de datos")
        return False

    def _update_user_profile_chat_id(self, email, chat_id):
        """Actualiza el perfil del usuario con el chat_id"""
        user_dir = self.user_manager._get_user_dir(email)
        profile_file = user_dir / "profile.json"

        if profile_file.exists():
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)

                profile['chat_id'] = chat_id
                profile['telegram_linked'] = True

                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(profile, f, indent=4, ensure_ascii=False)

                print(f"✅ Perfil actualizado para {email} con chat_id: {chat_id}")

            except Exception as e:
                print(f"Error actualizando perfil: {e}")

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
            return False, f"No se encontró chat_id para el usuario: {email}"

    def broadcast_to_all_users(self, text, parse_mode='HTML'):
        """Envía un mensaje a todos los usuarios registrados"""
        results = {}
        for email, chat_id in self.chat_ids.items():
            success, result = self.send_message(chat_id, text, parse_mode)
            results[email] = {
                'success': success,
                'result': result
            }
        return results

    def get_me(self):
        """Obtiene información del bot"""
        url = f"{self.base_url}/getMe"
        response = requests.get(url)
        return response.json()

    def get_user_chat_id(self, email):
        """Obtiene el chat_id de un usuario por email"""
        return self.chat_ids.get(email)

    def list_linked_users(self):
        """Lista todos los usuarios vinculados con sus chat_ids"""
        print("\n🤖 USUARIOS VINCULADOS CON TELEGRAM:")
        print("-" * 50)

        if not self.chat_ids:
            print("No hay usuarios vinculados")
            return

        for email, chat_id in self.chat_ids.items():
            user_dir = self.user_manager._get_user_dir(email)
            profile_file = user_dir / "profile.json"

            telegram_name = "Desconocido"
            if profile_file.exists():
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    telegram_name = profile.get('telegram', 'Desconocido')
                except:
                    pass

            print(f"📧 {email}")
            print(f"   👤 Telegram: {telegram_name}")
            print(f"   💬 Chat ID: {chat_id}")
            print()


# Uso del bot unificado
if __name__ == "__main__":
    # Configuración
    BOT_TOKEN = "8587676832:AAHx9szhD1mjCJXzlHHN81aR90aPh3j7w-I"

    # Crear instancia del bot unificado
    bot = TelegramBot(BOT_TOKEN)

    # Verificar que el bot funciona
    bot_info = bot.get_me()
    if bot_info['ok']:
        bot_name = bot_info['result']['first_name']
        print(f"🤖 Bot conectado: {bot_name}")
    else:
        print("❌ Error conectando con el bot")
        exit()

    # Obtener actualizaciones y vincular usuarios
    print("\n🔄 Buscando actualizaciones y vinculando usuarios...")
    bot.get_updates()

    # Mostrar usuarios vinculados
    bot.list_linked_users()

    # Ejemplo: Enviar mensaje a un usuario específico
    # bot.send_message_to_user("usuario@ejemplo.com", "¡Hola! Este es un mensaje personalizado")

    # Ejemplo: Broadcast a todos los usuarios
    # results = bot.broadcast_to_all_users("📢 Mensaje importante para todos los usuarios")
    # print(f"Resultados del broadcast: {results}")