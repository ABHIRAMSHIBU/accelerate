"""
Unit tests for TelegramInterface class.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

from japa.telegram_interface import TelegramInterface


class TestTelegramInterface(unittest.TestCase):
    """Test cases for TelegramInterface class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = os.path.join(self.temp_dir.name, "config.json")
        self.users_file = os.path.join(self.temp_dir.name, "users.json")
        
        # Sample config data
        self.config_data = {
            "test_service": {
                "health_check": "test_health_command",
                "restart": "test_restart_command",
                "rebuild": "test_rebuild_command"
            }
        }
        
        # Write config to file
        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f)
        
        # Create patches
        self.japa_patch = patch("japa.telegram_interface.JAPA")
        self.telegram_bot_patch = patch("japa.telegram_interface.TelegramBot")
        
        # Start patches
        self.mock_japa = self.japa_patch.start()
        self.mock_telegram_bot = self.telegram_bot_patch.start()
        
        # Configure mocks
        self.mock_japa_instance = MagicMock()
        self.mock_japa.return_value = self.mock_japa_instance
        
        self.mock_telegram_bot_instance = MagicMock()
        self.mock_telegram_bot.return_value = self.mock_telegram_bot_instance
        
        # Create TelegramInterface instance
        self.interface = TelegramInterface(
            self.config_file,
            "test_token",
            self.users_file
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop patches
        self.japa_patch.stop()
        self.telegram_bot_patch.stop()
        
        # Remove temporary directory
        self.temp_dir.cleanup()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.interface.japa, self.mock_japa_instance)
        self.assertEqual(self.interface.telegram_bot, self.mock_telegram_bot_instance)
        self.assertEqual(self.interface.users_file, self.users_file)
        self.assertEqual(self.interface.registered_users, set())
        
        # Verify JAPA and TelegramBot were created correctly
        self.mock_japa.assert_called_once_with(self.config_file)
        self.mock_telegram_bot.assert_called_once_with("test_token")
        
        # Verify handler was registered with JAPA
        self.mock_japa_instance.register_handler.assert_called_once()
    
    def test_register_user(self):
        """Test registering a user."""
        # Call method
        self.interface.register_user(123)
        
        # Verify user was added
        self.assertIn(123, self.interface.registered_users)
        
        # Verify users file was created
        self.assertTrue(os.path.exists(self.users_file))
        with open(self.users_file, 'r') as f:
            users_data = json.load(f)
            self.assertIn(123, users_data["users"])
    
    def test_unregister_user(self):
        """Test unregistering a user."""
        # Add user first
        self.interface.register_user(123)
        
        # Call method
        result = self.interface.unregister_user(123)
        
        # Verify
        self.assertTrue(result)
        self.assertNotIn(123, self.interface.registered_users)
        
        # Verify users file was updated
        with open(self.users_file, 'r') as f:
            users_data = json.load(f)
            self.assertNotIn(123, users_data["users"])
    
    def test_unregister_user_not_registered(self):
        """Test unregistering a user that is not registered."""
        result = self.interface.unregister_user(123)
        self.assertFalse(result)
    
    @patch("asyncio.create_task")
    def test_notification_handler_failure(self, mock_create_task):
        """Test notification handler for an unhealthy service."""
        self.interface.notification_handler("test_service", False, "Service is unhealthy")
        mock_create_task.assert_called_once()
    
    @patch("asyncio.create_task")
    def test_notification_handler_success(self, mock_create_task):
        """Test notification handler for a healthy service."""
        # Should not notify for healthy services
        self.interface.notification_handler("test_service", True, "Service is healthy")
        mock_create_task.assert_not_called()
    
    async def test_notify_users(self):
        """Test notifying users."""
        # Add some users
        self.interface.registered_users = {123, 456}
        
        # Configure mock
        self.interface.telegram_bot.send_message = AsyncMock()
        
        # Call method
        await self.interface._notify_users("Test message")
        
        # Verify
        self.assertEqual(self.interface.telegram_bot.send_message.call_count, 2)
    
    async def test_handle_start(self):
        """Test handling the /start command."""
        # Create mock update
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 123
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Call method
        await self.interface._handle_start(update, context)
        
        # Verify
        self.assertIn(123, self.interface.registered_users)
        update.message.reply_text.assert_called_once()
    
    async def test_handle_stop(self):
        """Test handling the /stop command."""
        # Add user first
        self.interface.register_user(123)
        
        # Create mock update
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 123
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Call method
        await self.interface._handle_stop(update, context)
        
        # Verify
        self.assertNotIn(123, self.interface.registered_users)
        update.message.reply_text.assert_called_once()
    
    async def test_handle_list_services(self):
        """Test handling the /list command."""
        # Configure mock
        self.interface.japa.config.get_services.return_value = ["service1", "service2"]
        
        # Create mock update
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Call method
        await self.interface._handle_list_services(update, context)
        
        # Verify
        update.message.reply_text.assert_called_once()
    
    async def test_handle_status_all(self):
        """Test handling the /status command for all services."""
        # Configure mock
        self.interface.japa.get_all_services_status.return_value = {
            "service1": True,
            "service2": False
        }
        
        # Create mock update
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        
        # Call method
        await self.interface._handle_status(update, context)
        
        # Verify
        update.message.reply_text.assert_called_once()
    
    async def test_handle_status_specific(self):
        """Test handling the /status command for a specific service."""
        # Configure mock
        self.interface.japa.check_health.return_value = {
            "service1": (True, "Service is healthy")
        }
        
        # Create mock update
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = ["service1"]
        
        # Call method
        await self.interface._handle_status(update, context)
        
        # Verify
        update.message.reply_text.assert_called_once()
    
    async def test_handle_restart_service(self):
        """Test handling the /restart command."""
        # Configure mock
        self.interface.japa.restart_service.return_value = (True, "Service restarted")
        
        # Create mock update
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = ["service1"]
        
        # Call method
        await self.interface._handle_restart_service(update, context)
        
        # Verify
        self.interface.japa.restart_service.assert_called_once_with("service1")
        self.assertEqual(update.message.reply_text.call_count, 2)
    
    async def test_handle_rebuild_service(self):
        """Test handling the /rebuild command."""
        # Configure mock
        self.interface.japa.rebuild_service.return_value = (True, "Service rebuilt")
        
        # Create mock update
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        # Create mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = ["service1"]
        
        # Call method
        await self.interface._handle_rebuild_service(update, context)
        
        # Verify
        self.interface.japa.rebuild_service.assert_called_once_with("service1")
        self.assertEqual(update.message.reply_text.call_count, 2)
    
    async def test_start(self):
        """Test starting the interface."""
        # Configure mocks
        self.interface.japa.start_health_monitoring = MagicMock()
        self.interface.telegram_bot.start_bot = AsyncMock()
        
        # Call method
        await self.interface.start()
        
        # Verify
        self.interface.japa.start_health_monitoring.assert_called_once()
        self.interface.telegram_bot.start_bot.assert_called_once()
    
    async def test_stop(self):
        """Test stopping the interface."""
        # Configure mocks
        self.interface.japa.stop_health_monitoring = MagicMock()
        self.interface.telegram_bot.stop_bot = AsyncMock()
        
        # Call method
        await self.interface.stop()
        
        # Verify
        self.interface.japa.stop_health_monitoring.assert_called_once()
        self.interface.telegram_bot.stop_bot.assert_called_once()


if __name__ == "__main__":
    unittest.main() 