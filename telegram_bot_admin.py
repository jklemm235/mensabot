"""
TelegramBotAdmin class for managing Telegram Bot API interactions.
Handles polling, sending messages, registering commands, and setting bot info.
"""
from typing import Optional, Dict, Callable
import requests


class TelegramBotAdmin:
    """
    Manages all Telegram Bot API interactions including:
    - Polling for updates
    - Sending messages
    - Registering commands
    - Setting bot profile (name, description, photo)
    - Auto-handling help messages
    """

    def __init__(self, token: str):
        """
        Initialize the Telegram Bot Admin.

        Args:
            token: Telegram Bot API token
        """
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.commands: Dict[str, str] = {}
        self.command_handlers: Dict[str, Callable] = {}
        self.last_handled_id: Optional[int] = None

        # Automatically register the help command
        self.register_command("help", "Show this help message", self._handle_help)

    def register_command(self, command: str, description: str, handler: Optional[Callable] = None) -> None:
        """
        Register a command with its description and optional handler.

        Args:
            command: Command name (without the / prefix)
            description: Description of what the command does
            handler: Optional function to handle the command. If None, command
                     is just registered for display in help.
        """
        self.commands[command] = description
        if handler:
            self.command_handlers[command] = handler

    def set_bot_commands(self) -> bool:
        """
        Register all commands with the Telegram API.
        This makes them appear in the user's command menu.

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/setMyCommands"

        # Validate command descriptions
        for cmd, desc in self.commands.items():
            if len(desc) > 255:
                print(f"Warning: Description for command '{cmd}' is too long: {len(desc)} characters. Max is 255.")
                raise ValueError(f"Description for command '{cmd}' is too long: {len(desc)} characters. Max is 255.")

        payload = [{"command": cmd, "description": desc} for cmd, desc in self.commands.items()]

        try:
            response = requests.post(url, json={"commands": payload})
            if response.status_code == 200:
                print("Commands reported successfully to Telegram API.")
                print(response.text)
                return True
            else:
                print(f"Failed to set commands: {response.text}")
                return False
        except Exception as e:
            print(f"Error setting commands: {e}")
            return False

    def set_bot_name(self, name: str, language_code: Optional[str] = None) -> bool:
        """
        Set the bot's name.

        Args:
            name: New bot name; 0-64 characters
            language_code: Optional two-letter ISO 639-1 language code

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/setMyName"
        params = {"name": name}
        if language_code:
            params["language_code"] = language_code

        try:
            response = requests.post(url, json=params)
            return response.status_code == 200
        except Exception as e:
            print(f"Error setting bot name: {e}")
            return False

    def set_bot_description(self, description: str, language_code: Optional[str] = None) -> bool:
        """
        Set the bot's description (shown in chat with bot if chat is empty).

        Args:
            description: New bot description; 0-512 characters
            language_code: Optional two-letter ISO 639-1 language code

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/setMyDescription"
        params = {"description": description}
        if language_code:
            params["language_code"] = language_code

        try:
            response = requests.post(url, json=params)
            return response.status_code == 200
        except Exception as e:
            print(f"Error setting bot description: {e}")
            return False

    def set_bot_short_description(self, short_description: str, language_code: Optional[str] = None) -> bool:
        """
        Set the bot's short description (shown on bot's profile page).

        Args:
            short_description: New short description; 0-120 characters
            language_code: Optional two-letter ISO 639-1 language code

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/setMyShortDescription"
        params = {"short_description": short_description}
        if language_code:
            params["language_code"] = language_code

        try:
            response = requests.post(url, json=params)
            return response.status_code == 200
        except Exception as e:
            print(f"Error setting bot short description: {e}")
            return False

    def set_bot_photo(self, photo_path: str) -> bool:
        """
        Set a new profile photo for the bot.

        Args:
            photo_path: Path to the photo file

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/setChatPhoto"

        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                response = requests.post(url, files=files)
                return response.status_code == 200
        except Exception as e:
            print(f"Error setting bot photo: {e}")
            return False

    def poll_updates(self, timeout: int = 3600, auto_handle_help: bool = True) -> Optional[Dict]:
        """
        Poll for new updates from Telegram using long polling.
        Returns one update at a time, processing it automatically.
        Auto-handles /help commands by default.

        Automatically tracks the last handled update ID internally.

        Args:
            timeout: Timeout in seconds for long polling (default 1 hour)
            auto_handle_help: If True, automatically respond to /help commands

        Returns:
            Dictionary with 'update_id', 'chat_id', 'message_text', and 'handled' flag if a valid update is found,
            None if no updates or an error occurred
        """
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": timeout, "limit": 1}  # Only fetch one update at a time

        if self.last_handled_id is not None:
            params["offset"] = self.last_handled_id + 1
            # Poll new updates only

        try:
            response = requests.get(url, params=params, timeout=timeout + 5)
            if response.status_code != 200:
                return None

            data = response.json()
            if not data.get("ok") or not data.get("result"):
                return None

            # Process the first (and only) update
            update = data["result"][0]
            processed = self.process_update(update, auto_handle_help=auto_handle_help)

            # Update the last_handled_id if we got a valid update
            if processed is not None:
                self.last_handled_id = processed['update_id']

            return processed

        except Exception as e:
            print(f"Error polling updates: {e}")
            return None

    def send_message(self, chat_id: int, text: str,
                     reply_markup: Optional[dict] = None,
                     parse_mode: Optional[str] = None,
                     disable_notification: bool = False) -> bool:
        """
        Send a text message to a chat.

        Args:
            chat_id: Unique identifier for the target chat
            text: Text of the message to send
            reply_markup: Optional inline keyboard markup
            parse_mode: Optional parse mode (e.g., "Markdown", "HTML")
            disable_notification: Send message silently

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            print(f"Sending message to chat {chat_id}: {text}")
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                print(f"Failed to send message: {response.text}")
                return False
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def _handle_help(self, message_text: str, chat_id: int, **kwargs) -> str:
        """
        Internal handler for the /help command.
        Generates help text from registered commands.

        Args:
            message_text: The message text (not used)
            chat_id: Chat ID (not used)
            **kwargs: Additional arguments (not used)

        Returns:
            Help message text
        """
        return "\n".join([f"/{cmd}: {desc}" for cmd, desc in self.commands.items()])

    def get_command_handler(self, command: str) -> Optional[Callable]:
        """
        Get the handler function for a command.

        Args:
            command: Command name (without / prefix)

        Returns:
            Handler function if registered, None otherwise
        """
        return self.command_handlers.get(command)

    def extract_command(self, message_text: str) -> Optional[str]:
        """
        Extract command name from message text.

        Args:
            message_text: The message text

        Returns:
            Command name without /, or None if not a command
        """
        if not message_text.startswith("/"):
            return None

        # Extract command (everything between / and first space or end)
        command_with_slash = message_text.split()[0]
        return command_with_slash[1:]  # Remove the /

    def process_update(self, update: dict, auto_handle_help: bool = True) -> Optional[Dict]:
        """
        Process a single update and extract relevant information.
        Automatically handles /help command if auto_handle_help is True.

        Args:
            update: Update dictionary from Telegram API
            auto_handle_help: If True, automatically respond to /help commands

        Returns:
            Dictionary with 'update_id', 'chat_id', 'user_id', 'chat_type', 'message_text', and 'handled' flag.
            If 'handled' is True, the message was auto-handled (e.g., help command).
            Returns None only for invalid updates or bot's own messages.
        """
        print(f"Processing update: {update}")
        update_id = update.get('update_id')
        # Message handling has started so update last_handled_id
        self.last_handled_id = update_id

        try:
            chat_id = update['message']['chat']['id']
            chat_type = update['message']['chat'].get('type', 'private')  # private, group, supergroup, or channel
        except KeyError:
            print(f"Update {update_id} does not contain a message or chat ID. Skipping.")
            return None

        try:
            user_id = update['message']['from']['id']
        except KeyError:
            print(f"Update {update_id} does not contain user ID. Skipping.")
            return None

        try:
            message_text = update['message']['text']
        except KeyError:
            print(f"Update {update_id} does not contain a text message. Skipping.")
            return None

        # Check if this message is from the bot itself - if so, skip it
        try:
            from_user = update['message'].get('from', {})
            if from_user.get('is_bot', False):
                print(f"Update {update_id} is from a bot (possibly this bot). Skipping.")
                return {
                    'update_id': update_id,
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'chat_type': chat_type,
                    'message_text': message_text,
                    'handled': True  # Mark as handled so it gets skipped
                }
        except KeyError:
            pass  # If we can't determine, continue processing

        # Auto-handle help command
        # and handle normal commands by returning them
        if auto_handle_help and message_text.startswith("/help"):
            help_text = self._handle_help(message_text, chat_id)
            self.send_message(chat_id, help_text)
            return {
                'update_id': update_id,
                'chat_id': chat_id,
                'user_id': user_id,
                'chat_type': chat_type,
                'message_text': message_text,
                'handled': True
            }
        return {
            'update_id': update_id,
            'chat_id': chat_id,
            'user_id': user_id,
            'chat_type': chat_type,
            'message_text': message_text,
            'handled': False
        }
