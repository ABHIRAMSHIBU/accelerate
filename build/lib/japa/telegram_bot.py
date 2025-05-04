"""
TelegramBot class for communication with Telegram API.
"""
import asyncio
import logging
import socket
from typing import Callable, Dict, List, Any, Optional, Awaitable

import telegram
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler,
)


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("TelegramBot")


class TelegramBot:
    """
    Handles communication with the Telegram Bot API.
    """
    
    def __init__(self, token: str, debug: bool = False):
        """
        Initialize the Telegram bot.
        
        Args:
            token: Telegram Bot API token
            debug: Enable debug mode with extra logging
        """
        self.token = token
        self.debug = debug
        
        if debug:
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("telegram").setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        
        logger.info(f"Initializing Telegram bot with token: {token[:5]}...{token[-5:]}")
        self.bot = telegram.Bot(token=token)
        self.application = None
        self.command_handlers: Dict[str, Callable] = {}
        self.webhook_mode = False
        self.webhook_url = None
    
    async def send_message(self, chat_id: int, text: str) -> bool:
        """
        Send a message to a Telegram chat.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            logger.debug(f"Sending message to {chat_id}: {text[:50]}...")
            await self.bot.send_message(chat_id=chat_id, text=text)
            logger.debug(f"Message sent to {chat_id} successfully")
            return True
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {str(e)}")
            return False
    
    def broadcast_message(self, chat_ids: List[int], text: str) -> None:
        """
        Send a message to multiple chats.
        
        Args:
            chat_ids: List of Telegram chat IDs
            text: Message text
        """
        logger.debug(f"Broadcasting message to {len(chat_ids)} users: {text[:50]}...")
        for chat_id in chat_ids:
            asyncio.create_task(self.send_message(chat_id, text))
    
    def register_command_handler(self, command: str, handler_func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]) -> None:
        """
        Register a command handler.
        
        Args:
            command: Command name (without slash)
            handler_func: Async function that handles the command
        """
        logger.debug(f"Registering command handler for /{command}")
        self.command_handlers[command] = handler_func
    
    async def _handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle unknown commands.
        """
        if update.effective_chat:
            logger.debug(f"Received unknown command from user {update.effective_user.id}: {update.message.text}")
            await update.message.reply_text(
                "Sorry, I don't understand that command. Send /help to see available commands."
            )
    
    async def _handle_debug_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Log any received message for debugging.
        """
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
        text = update.message.text if update.message else "No text"
        
        logger.debug(f"Received message - User: {user_id}, Chat: {chat_id}, Text: {text}")
    
    async def _check_bot_info(self) -> bool:
        """
        Check if the bot is correctly connected to Telegram.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            logger.info("Checking bot connection to Telegram...")
            bot_info = await self.bot.get_me()
            logger.info(f"Bot connected successfully. Username: @{bot_info.username}, ID: {bot_info.id}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Telegram: {str(e)}")
            return False
    
    def _get_public_ip(self) -> Optional[str]:
        """
        Try to get the public IP address of this machine.
        
        Returns:
            str or None: Public IP address or None if not found
        """
        try:
            # Try to get the public IP by connecting to a well-known server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            logger.info(f"Detected local IP: {local_ip}")
            return local_ip
        except Exception as e:
            logger.error(f"Could not determine public IP: {str(e)}")
            return None
    
    async def start_bot(self, use_webhook: bool = False, webhook_url: Optional[str] = None, 
                        webhook_port: int = 8443, cert_path: Optional[str] = None) -> None:
        """
        Start the Telegram bot.
        
        Args:
            use_webhook: Whether to use webhooks instead of polling
            webhook_url: URL for the webhook (e.g., https://example.com:8443)
            webhook_port: Port to listen on for webhooks
            cert_path: Path to SSL certificate for webhooks
        """
        logger.info("Starting Telegram bot...")
        
        # Check bot connection first
        if not await self._check_bot_info():
            logger.error("Failed to connect to Telegram API. Bot will not receive messages.")
            return
        
        # Updated for python-telegram-bot v20+
        self.application = Application.builder().token(self.token).build()
        
        # Register all command handlers
        for command, handler_func in self.command_handlers.items():
            logger.debug(f"Adding command handler for /{command}")
            self.application.add_handler(CommandHandler(command, handler_func))
        
        # Add handler for unknown commands
        self.application.add_handler(MessageHandler(filters.COMMAND, self._handle_unknown_command))
        
        # Add debug message handler if in debug mode
        if self.debug:
            logger.debug("Adding debug message handler")
            self.application.add_handler(MessageHandler(filters.ALL, self._handle_debug_message), group=999)
        
        # Start the bot
        logger.info("Initializing application...")
        await self.application.initialize()
        
        if use_webhook and webhook_url:
            self.webhook_mode = True
            self.webhook_url = webhook_url
            
            # Set up the webhook
            logger.info(f"Setting up webhook at {webhook_url}")
            
            webhook_info = await self.bot.get_webhook_info()
            if webhook_info.url:
                logger.info(f"Removing existing webhook: {webhook_info.url}")
                await self.bot.delete_webhook()
            
            # Set the webhook
            webhook_success = False
            try:
                if cert_path:
                    # With self-signed certificate
                    with open(cert_path, 'rb') as cert_file:
                        await self.bot.set_webhook(url=webhook_url, certificate=cert_file.read())
                else:
                    # Without certificate (requires valid SSL certificate on server)
                    await self.bot.set_webhook(url=webhook_url)
                
                # Verify the webhook was set correctly
                webhook_info = await self.bot.get_webhook_info()
                if webhook_info.url == webhook_url:
                    logger.info(f"Webhook set successfully to {webhook_info.url}")
                    webhook_success = True
                else:
                    logger.error(f"Failed to set webhook. Current webhook: {webhook_info.url}")
            except Exception as e:
                logger.error(f"Error setting webhook: {str(e)}")
            
            if webhook_success:
                # Start the webhook
                ip = "0.0.0.0"  # Listen on all interfaces
                
                logger.info(f"Starting webhook on {ip}:{webhook_port}")
                await self.application.start_webhook(
                    listen=ip,
                    port=webhook_port,
                    url_path=self.token,
                    webhook_url=webhook_url
                )
                logger.info(f"Webhook is running at {webhook_url}")
            else:
                logger.error("Falling back to polling mode due to webhook setup failure")
                await self.application.updater.start_polling()
        else:
            # Use polling
            logger.info("Starting polling for updates...")
            await self.application.updater.start_polling()
            logger.info("Bot is now running in polling mode!")
    
    async def stop_bot(self) -> None:
        """
        Stop the Telegram bot.
        """
        logger.info("Stopping Telegram bot...")
        
        if self.webhook_mode and self.webhook_url:
            try:
                logger.info("Removing webhook...")
                await self.bot.delete_webhook()
                logger.info("Webhook removed successfully")
            except Exception as e:
                logger.error(f"Error removing webhook: {str(e)}")
        
        if self.application:
            if hasattr(self.application, 'updater') and self.application.updater and self.application.updater.running:
                await self.application.updater.stop()
            
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped successfully")
        else:
            logger.info("Bot was not running") 