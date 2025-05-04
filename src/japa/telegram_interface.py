"""
TelegramInterface class for connecting JAPA with Telegram.
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Set, Optional, Any

from telegram import Update
from telegram.ext import ContextTypes

from .japa import JAPA
from .telegram_bot import TelegramBot

# Configure logging
logger = logging.getLogger("TelegramInterface")


class TelegramInterface:
    """
    Interface between JAPA and Telegram.
    """
    
    def __init__(self, config_file: str, telegram_token: str, users_file: str = "users.json", debug: bool = False):
        """
        Initialize the TelegramInterface.
        
        Args:
            config_file: Path to the JAPA configuration file
            telegram_token: Telegram Bot API token
            users_file: Path to the file to store registered users
            debug: Enable debug mode with extra logging
        """
        if debug:
            logger.setLevel(logging.DEBUG)
        
        logger.info(f"Initializing JAPA with config file: {config_file}")
        self.japa = JAPA(config_file)
        
        logger.info(f"Initializing TelegramBot with token: {telegram_token[:5]}...{telegram_token[-5:]}")
        self.telegram_bot = TelegramBot(telegram_token, debug=debug)
        
        self.users_file = users_file
        self.registered_users: Set[int] = set()
        self.loop = None
        self.debug = debug
        
        # Load registered users from file
        self.load_users()
        
        # Register the notification handler with JAPA
        logger.info("Registering notification handler")
        self.japa.register_handler(self.notification_handler)
        
        # Register command handlers with the Telegram bot
        logger.info("Registering command handlers")
        self._register_command_handlers()
    
    def load_users(self) -> None:
        """
        Load registered users from file.
        """
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    self.registered_users = set(users_data.get('users', []))
                logger.info(f"Loaded {len(self.registered_users)} registered users from {self.users_file}")
            except Exception as e:
                logger.error(f"Error loading users: {str(e)}")
        else:
            logger.info(f"Users file {self.users_file} does not exist, starting with empty user list")
    
    def save_users(self) -> None:
        """
        Save registered users to file.
        """
        try:
            with open(self.users_file, 'w') as f:
                json.dump({'users': list(self.registered_users)}, f)
            logger.debug(f"Saved {len(self.registered_users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {str(e)}")
    
    def register_user(self, user_id: int) -> None:
        """
        Register a user to receive notifications.
        
        Args:
            user_id: Telegram user ID
        """
        logger.info(f"Registering user: {user_id}")
        self.registered_users.add(user_id)
        self.save_users()
    
    def unregister_user(self, user_id: int) -> bool:
        """
        Unregister a user from notifications.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user was unregistered, False otherwise
        """
        if user_id in self.registered_users:
            logger.info(f"Unregistering user: {user_id}")
            self.registered_users.remove(user_id)
            self.save_users()
            return True
        logger.debug(f"Attempted to unregister non-registered user: {user_id}")
        return False
    
    def notification_handler(self, service_name: str, status: bool, message: str) -> None:
        """
        Handle notifications from JAPA.
        
        Args:
            service_name: Name of the service
            status: Status of the service (True = healthy, False = unhealthy)
            message: Message with details
        """
        # Only notify users about failures
        if not status:
            status_text = "❌ UNHEALTHY" if not status else "✅ HEALTHY"
            notification = f"{status_text}: {service_name}\n{message}"
            
            logger.info(f"Notification to send: {notification}")
            
            # Store the notification to send it when the event loop is running
            if self.loop and self.loop.is_running():
                logger.debug("Scheduling notification for delivery")
                asyncio.run_coroutine_threadsafe(self._notify_users(notification), self.loop)
            else:
                logger.error(f"Cannot send notification - No running event loop")
    
    async def _notify_users(self, message: str) -> None:
        """
        Notify all registered users.
        
        Args:
            message: Message to send
        """
        if not self.registered_users:
            logger.warning("No registered users to notify")
            return
            
        logger.info(f"Notifying {len(self.registered_users)} users")
        for user_id in self.registered_users:
            await self.telegram_bot.send_message(user_id, message)
    
    def _register_command_handlers(self) -> None:
        """
        Register command handlers with the Telegram bot.
        """
        self.telegram_bot.register_command_handler("start", self._handle_start)
        self.telegram_bot.register_command_handler("stop", self._handle_stop)
        self.telegram_bot.register_command_handler("status", self._handle_status)
        self.telegram_bot.register_command_handler("list", self._handle_list_services)
        self.telegram_bot.register_command_handler("restart", self._handle_restart_service)
        self.telegram_bot.register_command_handler("rebuild", self._handle_rebuild_service)
        self.telegram_bot.register_command_handler("help", self._handle_help)
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /start command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        logger.info(f"Received /start command from user {user_id} (@{user_name})")
        
        self.register_user(user_id)
        await update.message.reply_text(
            f"Welcome to JAPA, @{user_name}! You will receive notifications about service health."
        )
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /stop command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        logger.info(f"Received /stop command from user {user_id} (@{user_name})")
        
        if self.unregister_user(user_id):
            await update.message.reply_text("You have been unregistered from notifications.")
        else:
            await update.message.reply_text("You were not registered.")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /help command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        logger.info(f"Received /help command from user {user_id} (@{user_name})")
        
        help_text = (
            "🤖 *JAPA Bot Commands* 🤖\n\n"
            "/start - Start receiving notifications\n"
            "/stop - Stop receiving notifications\n"
            "/status [service] - Check status of all services or a specific service\n"
            "/list - List all configured services\n"
            "/restart <service> - Restart a specific service\n"
            "/rebuild <service> - Rebuild a specific service\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /status command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        args = context.args
        
        if not args:
            logger.info(f"Received /status command (all services) from user {user_id} (@{user_name})")
            # Get status of all services
            statuses = self.japa.get_all_services_status()
            if not statuses:
                await update.message.reply_text("No service status available yet.")
                return
            
            status_lines = []
            for service, status in statuses.items():
                status_text = "✅ HEALTHY" if status else "❌ UNHEALTHY"
                status_lines.append(f"{service}: {status_text}")
            
            await update.message.reply_text("\n".join(status_lines))
        else:
            service = args[0]
            logger.info(f"Received /status command for service '{service}' from user {user_id} (@{user_name})")
            
            # Get status of specific service
            results = self.japa.check_health(service)
            
            if service not in results:
                logger.warning(f"Service '{service}' not found")
                await update.message.reply_text(f"Service {service} not found.")
                return
            
            status, message = results[service]
            status_text = "✅ HEALTHY" if status else "❌ UNHEALTHY"
            await update.message.reply_text(f"{service}: {status_text}\n{message}")
    
    async def _handle_list_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /list command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        logger.info(f"Received /list command from user {user_id} (@{user_name})")
        
        services = self.japa.config.get_services()
        if not services:
            await update.message.reply_text("No services configured.")
        else:
            await update.message.reply_text("Available services:\n" + "\n".join(services))
    
    async def _handle_restart_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /restart command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        args = context.args
        
        if not args:
            logger.info(f"Received /restart command without service name from user {user_id} (@{user_name})")
            await update.message.reply_text("Please specify a service to restart.")
            return
        
        service = args[0]
        logger.info(f"Received /restart command for service '{service}' from user {user_id} (@{user_name})")
        
        await update.message.reply_text(f"Restarting {service}...")
        
        success, message = self.japa.restart_service(service)
        status_text = "✅ Success" if success else "❌ Failed"
        
        logger.info(f"Restart service '{service}' result: {status_text}, message: {message}")
        await update.message.reply_text(f"{status_text}: {message}")
    
    async def _handle_rebuild_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /rebuild command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        args = context.args
        
        if not args:
            logger.info(f"Received /rebuild command without service name from user {user_id} (@{user_name})")
            await update.message.reply_text("Please specify a service to rebuild.")
            return
        
        service = args[0]
        logger.info(f"Received /rebuild command for service '{service}' from user {user_id} (@{user_name})")
        
        await update.message.reply_text(f"Rebuilding {service}...")
        
        success, message = self.japa.rebuild_service(service)
        status_text = "✅ Success" if success else "❌ Failed"
        
        logger.info(f"Rebuild service '{service}' result: {status_text}, message: {message}")
        await update.message.reply_text(f"{status_text}: {message}")
    
    async def start(self, webhook_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Start the TelegramInterface.
        
        Args:
            webhook_config: Optional webhook configuration for the TelegramBot
        """
        logger.info("Starting TelegramInterface")
        
        # Store the event loop for later use in notifications
        self.loop = asyncio.get_running_loop()
        
        # Start JAPA health monitoring
        logger.info("Starting JAPA health monitoring")
        self.japa.start_health_monitoring()
        
        # Start the Telegram bot with webhook configuration if provided
        logger.info("Starting Telegram bot")
        if webhook_config:
            logger.info(f"Using webhook mode with URL: {webhook_config.get('webhook_url')}")
            await self.telegram_bot.start_bot(
                use_webhook=webhook_config.get("use_webhook", False),
                webhook_url=webhook_config.get("webhook_url"),
                webhook_port=webhook_config.get("webhook_port", 8443),
                cert_path=webhook_config.get("cert_path")
            )
        else:
            # Use polling mode
            logger.info("Using polling mode")
            await self.telegram_bot.start_bot()
    
    async def stop(self) -> None:
        """
        Stop the TelegramInterface.
        """
        logger.info("Stopping TelegramInterface")
        
        # Stop JAPA health monitoring
        logger.info("Stopping JAPA health monitoring")
        self.japa.stop_health_monitoring()
        
        # Stop the Telegram bot
        logger.info("Stopping Telegram bot")
        await self.telegram_bot.stop_bot() 