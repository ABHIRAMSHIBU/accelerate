"""
TelegramInterface class for connecting JAPA with Telegram.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional, Set, Any, Callable
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .japa import JAPA
from .telegram_bot import TelegramBot
from .user_database import UserDatabase

# Configure logging
logger = logging.getLogger("TelegramInterface")


def check_permission(required_role: str):
    """
    Decorator to check if a user has the required permission level.
    
    Args:
        required_role: Required role ("regular", "admin", "superadmin")
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            user_data = self.db.get_user(user_id)
            user_role = user_data["role"] if user_data else "regular"
            
            # Update last active timestamp
            if user_data:
                self.db.update_last_active(user_id)
            
            if required_role == "regular":
                permission = True
            elif required_role == "admin":
                permission = user_role in ["admin", "superadmin"]
            elif required_role == "superadmin":
                permission = user_role == "superadmin"
            else:
                permission = False
                
            if permission:
                return await func(self, update, context, *args, **kwargs)
            else:
                await update.message.reply_text(
                    f"⛔ You don't have permission to use this command. Required role: {required_role}."
                )
                return None
        return wrapper
    return decorator


class TelegramInterface:
    """
    Interface between JAPA and Telegram.
    """
    
    def __init__(self, japa: JAPA, telegram_token: str, db_path: str = "users.db", debug: bool = False, superadmin_ids: List[int] = None):
        """
        Initialize the TelegramInterface.
        
        Args:
            japa: JAPA instance
            telegram_token: Telegram Bot API token
            db_path: Path to the SQLite database file
            debug: Enable debug mode with extra logging
            superadmin_ids: List of Telegram user IDs to be set as superadmins
        """
        if debug:
            logger.setLevel(logging.DEBUG)
        
        logger.info("Initializing TelegramInterface")
        self.japa = japa
        
        logger.info(f"Initializing TelegramBot with token: {telegram_token[:5]}...{telegram_token[-5:]}")
        self.telegram_bot = TelegramBot(telegram_token, debug=debug)
        
        logger.info(f"Initializing UserDatabase with database file: {db_path}")
        self.db = UserDatabase(db_path, debug=debug)
        
        self.loop = None
        self.debug = debug
        self.superadmin_ids = superadmin_ids or []
        
        # Ensure superadmins are in the database
        for superadmin_id in self.superadmin_ids:
            self._ensure_superadmin(superadmin_id)
        
        # Register the notification handler with JAPA
        logger.info("Registering notification handler")
        self.japa.register_handler(self.notification_handler)
        
        # Register command handlers with the Telegram bot
        logger.info("Registering command handlers")
        self._register_command_handlers()
    
    def _ensure_superadmin(self, user_id: int) -> None:
        """
        Ensure a user is set as superadmin in the database.
        
        Args:
            user_id: Telegram user ID
        """
        user_data = self.db.get_user(user_id)
        if user_data:
            if user_data["role"] != "superadmin":
                logger.info(f"Updating user {user_id} to superadmin role")
                self.db.update_user_role(user_id, "superadmin")
        else:
            logger.info(f"Adding new superadmin user {user_id}")
            self.db.add_user(user_id, f"superadmin_{user_id}", "superadmin")
    
    def register_user(self, user_id: int, username: str, role: str = "regular") -> None:
        """
        Register a user to receive notifications.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            role: User role ("regular", "admin", "superadmin")
        """
        logger.info(f"Registering user: {user_id} (@{username})")
        self.db.add_user(user_id, username, role)
    
    def unregister_user(self, user_id: int) -> bool:
        """
        Unregister a user from notifications.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user was unregistered, False otherwise
        """
        if self.db.get_user(user_id):
            logger.info(f"Unregistering user: {user_id}")
            return self.db.remove_user(user_id)
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
        registered_users = self.db.get_registered_users()
        
        if not registered_users:
            logger.warning("No registered users to notify")
            return
            
        logger.info(f"Notifying {len(registered_users)} users")
        for user_id in registered_users:
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
        
        # New admin commands
        self.telegram_bot.register_command_handler("admins", self._handle_list_admins)
        self.telegram_bot.register_command_handler("promote", self._handle_promote_user)
        self.telegram_bot.register_command_handler("demote", self._handle_demote_user)
        self.telegram_bot.register_command_handler("remove", self._handle_remove_user)
        self.telegram_bot.register_command_handler("requestadmin", self._handle_request_admin)
    
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
        
        if not self.db.get_user(user_id):
            self.register_user(user_id, user_name)
            await update.message.reply_text(
                f"Welcome to JAPA, @{user_name}! You will receive notifications about service health."
            )
        else:
            self.db.update_last_active(user_id)
            await update.message.reply_text(
                f"Welcome back, @{user_name}! You're already registered."
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
        
        # Get user role
        user_data = self.db.get_user(user_id)
        user_role = user_data["role"] if user_data else "regular"
        
        # Update last active
        if user_data:
            self.db.update_last_active(user_id)
        
        # Base commands (available to all users)
        help_text = (
            "🤖 *JAPA Bot Commands* 🤖\n\n"
            "/start - Start receiving notifications\n"
            "/stop - Stop receiving notifications\n"
            "/status \\[service\\] - Check status of all services or a specific service\n"
            "/list - List all configured services\n"
            "/help - Show this help message"
        )
        
        # Admin commands
        if user_role in ["admin", "superadmin"]:
            help_text += (
                "\n\n🔑 *Admin Commands* 🔑\n"
                "/restart \\<service\\> - Restart a specific service\n"
                "/rebuild \\<service\\> - Rebuild a specific service"
            )
        else:
            help_text += (
                "\n\n💡 *Need Admin Access?* 💡\n"
                "/requestadmin \\[reason\\] - Request admin privileges"
            )
        
        # Superadmin commands
        if user_role == "superadmin":
            help_text += (
                "\n\n👑 *Superadmin Commands* 👑\n"
                "/admins - List all admins\n"
                "/promote \\<user\\_id\\> - Promote a user to admin\n"
                "/demote \\<user\\_id\\> - Demote an admin to regular user\n"
                "/remove \\<user\\_id\\> - Remove a user completely from the database"
            )
        
        # Try using HTML formatting instead of Markdown
        html_help_text = help_text.replace('*', '<b>').replace('</b></b>', '</b>')
        html_help_text = html_help_text.replace('\\[', '[').replace('\\]', ']')
        html_help_text = html_help_text.replace('\\<', '<').replace('\\>', '>')
        html_help_text = html_help_text.replace('\\_', '_')
        
        try:
            await update.message.reply_text(html_help_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send help message with HTML formatting: {str(e)}")
            # Fallback to plain text without formatting
            plain_text = help_text.replace('*', '').replace('\\[', '[').replace('\\]', ']')
            plain_text = plain_text.replace('\\<', '<').replace('\\>', '>').replace('\\_', '_')
            await update.message.reply_text(plain_text)
    
    @check_permission("regular")
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
    
    @check_permission("regular")
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
    
    @check_permission("admin")
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
    
    @check_permission("admin")
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
    
    @check_permission("superadmin")
    async def _handle_list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /admins command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        logger.info(f"Received /admins command from user {user_id} (@{user_name})")
        
        admins = self.db.get_users_by_role("admin")
        superadmins = self.db.get_users_by_role("superadmin")
        
        if not admins and not superadmins:
            await update.message.reply_text("No admins configured.")
            return
        
        lines = []
        
        if superadmins:
            lines.append("👑 *Superadmins*:")
            for admin in superadmins:
                # Escape special characters in username for Markdown
                safe_username = admin['username'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                lines.append(f"- {safe_username} (ID: {admin['user_id']})")
        
        if admins:
            if lines:
                lines.append("")
            lines.append("🔑 *Admins*:")
            for admin in admins:
                # Escape special characters in username for Markdown
                safe_username = admin['username'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                lines.append(f"- {safe_username} (ID: {admin['user_id']})")
        
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    
    @check_permission("superadmin")
    async def _handle_promote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /promote command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        args = context.args
        
        if not args:
            logger.info(f"Received /promote command without user ID from user {user_id} (@{user_name})")
            await update.message.reply_text("Please specify a user ID to promote.")
            return
        
        try:
            target_user_id = int(args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid user ID (numeric).")
            return
        
        logger.info(f"Received /promote command for user {target_user_id} from user {user_id} (@{user_name})")
        
        target_user = self.db.get_user(target_user_id)
        if not target_user:
            await update.message.reply_text(f"User with ID {target_user_id} not found. They need to start the bot first.")
            return
        
        if target_user["role"] == "admin":
            await update.message.reply_text(f"User {target_user['username']} is already an admin.")
            return
            
        if target_user["role"] == "superadmin":
            await update.message.reply_text(f"User {target_user['username']} is a superadmin and cannot be promoted further.")
            return
        
        if self.db.update_user_role(target_user_id, "admin"):
            logger.info(f"Promoted user {target_user_id} to admin")
            await update.message.reply_text(f"User {target_user['username']} has been promoted to admin.")
        else:
            logger.error(f"Failed to promote user {target_user_id}")
            await update.message.reply_text(f"Failed to promote user {target_user['username']}.")
    
    @check_permission("superadmin")
    async def _handle_demote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /demote command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        args = context.args
        
        if not args:
            logger.info(f"Received /demote command without user ID from user {user_id} (@{user_name})")
            await update.message.reply_text("Please specify a user ID to demote.")
            return
        
        try:
            target_user_id = int(args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid user ID (numeric).")
            return
        
        logger.info(f"Received /demote command for user {target_user_id} from user {user_id} (@{user_name})")
        
        # Don't allow demoting self
        if target_user_id == user_id:
            await update.message.reply_text("You cannot demote yourself.")
            return
        
        target_user = self.db.get_user(target_user_id)
        if not target_user:
            await update.message.reply_text(f"User with ID {target_user_id} not found.")
            return
        
        if target_user["role"] == "regular":
            await update.message.reply_text(f"User {target_user['username']} is already a regular user.")
            return
            
        if target_user["role"] == "superadmin" and target_user_id in self.superadmin_ids:
            await update.message.reply_text(f"User {target_user['username']} is a configured superadmin and cannot be demoted.")
            return
        
        if self.db.update_user_role(target_user_id, "regular"):
            logger.info(f"Demoted user {target_user_id} to regular")
            await update.message.reply_text(f"User {target_user['username']} has been demoted to regular user.")
        else:
            logger.error(f"Failed to demote user {target_user_id}")
            await update.message.reply_text(f"Failed to demote user {target_user['username']}.")
    
    @check_permission("regular")
    async def _handle_request_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /requestadmin command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        
        # Get reason from args
        reason = " ".join(context.args) if context.args else "No reason provided"
        
        logger.info(f"Received /requestadmin command from user {user_id} (@{user_name})")
        
        user_data = self.db.get_user(user_id)
        if not user_data:
            await update.message.reply_text("Please run /start first to register with the bot.")
            return
        
        if user_data["role"] in ["admin", "superadmin"]:
            await update.message.reply_text(f"You already have admin privileges.")
            return
        
        # Create the admin request
        request_id = self.db.create_admin_request(user_id, user_name, reason)
        
        if not request_id:
            await update.message.reply_text("Failed to create admin request. Please try again later.")
            return
        
        # Notify user
        await update.message.reply_text(
            "Your request for admin privileges has been submitted. "
            "A superadmin will review your request."
        )
        
        # Notify superadmins
        superadmins = self.db.get_users_by_role("superadmin")
        if not superadmins:
            logger.warning("No superadmins to notify about admin request")
            return
            
        # Create inline keyboard for approval/denial
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"deny_{request_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send request to all superadmins
        for admin in superadmins:
            admin_id = admin["user_id"]
            await self.telegram_bot.send_message(
                admin_id,
                f"Admin Request from {user_name} (ID: {user_id}):\n\nReason: {reason}",
                reply_markup=reply_markup
            )
    
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle callback queries from inline keyboards.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        # Check if user is a superadmin
        user_data = self.db.get_user(user_id)
        if not user_data or user_data["role"] != "superadmin":
            await query.edit_message_text("You don't have permission to perform this action.")
            return
        
        if data.startswith("approve_"):
            request_id = data.split("_")[1]
            success, message = self.db.approve_request(request_id)
            
            if success:
                await query.edit_message_text(f"✅ Request approved! {message}")
                
                # Get the user ID from the request
                request = self.db.get_request(request_id)
                if request:
                    # Notify the user about approval
                    await self.telegram_bot.send_message(
                        request["user_id"],
                        "🎉 Your request for admin privileges has been approved! "
                        "You can now use admin commands like /restart and /rebuild."
                    )
            else:
                await query.edit_message_text(f"❌ Failed to approve request: {message}")
                
        elif data.startswith("deny_"):
            request_id = data.split("_")[1]
            
            # Get the user ID from the request before denying it
            request = self.db.get_request(request_id)
            
            if self.db.deny_request(request_id):
                await query.edit_message_text("❌ Request denied.")
                
                if request:
                    # Notify the user about denial
                    await self.telegram_bot.send_message(
                        request["user_id"],
                        "Your request for admin privileges has been denied."
                    )
            else:
                await query.edit_message_text("Failed to deny request.")
    
    @check_permission("superadmin")
    async def _handle_remove_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /remove command.
        
        Args:
            update: Update object from Telegram
            context: Context object from Telegram
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        args = context.args
        
        if not args:
            logger.info(f"Received /remove command without user ID from user {user_id} (@{user_name})")
            await update.message.reply_text("Please specify a user ID to remove.")
            return
        
        try:
            target_user_id = int(args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid user ID (numeric).")
            return
        
        logger.info(f"Received /remove command for user {target_user_id} from user {user_id} (@{user_name})")
        
        # Don't allow removing self
        if target_user_id == user_id:
            await update.message.reply_text("You cannot remove yourself.")
            return
        
        # Don't allow removing other superadmins configured in the system
        if target_user_id in self.superadmin_ids:
            await update.message.reply_text("You cannot remove a configured superadmin.")
            return
        
        target_user = self.db.get_user(target_user_id)
        if not target_user:
            await update.message.reply_text(f"User with ID {target_user_id} not found.")
            return
        
        user_name_to_display = target_user['username']
        
        if self.db.remove_user(target_user_id):
            logger.info(f"Removed user {target_user_id} from the database")
            await update.message.reply_text(f"User {user_name_to_display} has been completely removed from the database.")
        else:
            logger.error(f"Failed to remove user {target_user_id}")
            await update.message.reply_text(f"Failed to remove user {user_name_to_display}.")
    
    async def start(self, webhook_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Start the TelegramInterface.
        
        Args:
            webhook_config: Optional webhook configuration for the TelegramBot
        """
        logger.info("Starting TelegramInterface")
        
        # Store the event loop for later use in notifications
        self.loop = asyncio.get_running_loop()
        
        # Register callback query handler for inline keyboard buttons
        self.telegram_bot.register_callback_query_handler(self._handle_callback_query)
        
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
        
        # Close the database connection
        logger.info("Closing database connection")
        self.db.close() 