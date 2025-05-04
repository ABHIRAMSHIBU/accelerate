"""
Unit tests for TelegramBot class.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update

from japa.telegram_bot import TelegramBot


class TestTelegramBot(unittest.TestCase):
    """Test cases for TelegramBot class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.token = "test_token"
        
        # Create patches
        self.bot_patch = patch("telegram.Bot")
        self.application_patch = patch("telegram.ext.Application")
        
        # Start patches
        self.mock_bot = self.bot_patch.start()
        self.mock_application = self.application_patch.start()
        
        # Configure mocks
        self.mock_bot_instance = MagicMock()
        self.mock_bot.return_value = self.mock_bot_instance
        
        self.mock_application_builder = MagicMock()
        self.mock_application.builder.return_value = self.mock_application_builder
        self.mock_application_instance = MagicMock()
        self.mock_application_builder.token.return_value = self.mock_application_builder
        self.mock_application_builder.build.return_value = self.mock_application_instance
        
        # Create TelegramBot instance
        self.telegram_bot = TelegramBot(self.token)
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop patches
        self.bot_patch.stop()
        self.application_patch.stop()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.telegram_bot.token, self.token)
        self.assertEqual(self.telegram_bot.bot, self.mock_bot_instance)
        self.assertEqual(self.telegram_bot.command_handlers, {})
        self.assertIsNone(self.telegram_bot.application)
        
        self.mock_bot.assert_called_once_with(token=self.token)
    
    @patch("asyncio.create_task")
    def test_broadcast_message(self, mock_create_task):
        """Test broadcasting a message to multiple chats."""
        chat_ids = [123, 456, 789]
        text = "Test message"
        
        # Configure mock
        self.telegram_bot.send_message = AsyncMock()
        
        # Call method
        self.telegram_bot.broadcast_message(chat_ids, text)
        
        # Verify each chat ID got a message
        self.assertEqual(mock_create_task.call_count, 3)
    
    def test_register_command_handler(self):
        """Test registering a command handler."""
        handler_func = AsyncMock()
        self.telegram_bot.register_command_handler("test", handler_func)
        
        self.assertEqual(self.telegram_bot.command_handlers["test"], handler_func)
    
    @patch("asyncio.create_task")
    async def test_start_bot(self, mock_create_task):
        """Test starting the bot."""
        # Add a command handler
        handler_func = AsyncMock()
        self.telegram_bot.register_command_handler("test", handler_func)
        
        # Call method
        await self.telegram_bot.start_bot()
        
        # Verify application was initialized and started
        self.assertEqual(self.telegram_bot.application, self.mock_application_instance)
        self.mock_application_builder.token.assert_called_once_with(self.token)
        self.mock_application_builder.build.assert_called_once()
        self.mock_application_instance.add_handler.assert_called_once()
        self.mock_application_instance.initialize.assert_called_once()
        self.mock_application_instance.start_polling.assert_called_once()
    
    async def test_stop_bot(self):
        """Test stopping the bot."""
        # Set application
        self.telegram_bot.application = self.mock_application_instance
        
        # Call method
        await self.telegram_bot.stop_bot()
        
        # Verify application was stopped
        self.mock_application_instance.stop.assert_called_once()
        self.mock_application_instance.shutdown.assert_called_once()
    
    async def test_stop_bot_no_application(self):
        """Test stopping the bot when no application exists."""
        # Set application to None
        self.telegram_bot.application = None
        
        # Call method (should not raise exceptions)
        await self.telegram_bot.stop_bot()
    
    async def test_send_message_success(self):
        """Test sending a message successfully."""
        chat_id = 123
        text = "Test message"
        
        # Configure mock
        self.mock_bot_instance.send_message = AsyncMock()
        
        # Call method
        result = await self.telegram_bot.send_message(chat_id, text)
        
        # Verify
        self.assertTrue(result)
        self.mock_bot_instance.send_message.assert_called_once_with(chat_id=chat_id, text=text)
    
    async def test_send_message_failure(self):
        """Test sending a message that fails."""
        chat_id = 123
        text = "Test message"
        
        # Configure mock to raise an exception
        self.mock_bot_instance.send_message = AsyncMock(side_effect=Exception("Test exception"))
        
        # Call method
        result = await self.telegram_bot.send_message(chat_id, text)
        
        # Verify
        self.assertFalse(result)
        self.mock_bot_instance.send_message.assert_called_once_with(chat_id=chat_id, text=text)


if __name__ == "__main__":
    unittest.main() 