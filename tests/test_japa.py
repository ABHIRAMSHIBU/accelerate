"""
Unit tests for JAPA class.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from japa.japa import JAPA


class TestJAPA(unittest.TestCase):
    """Test cases for JAPA class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary config file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = os.path.join(self.temp_dir.name, "config.json")
        
        # Sample config data
        self.config_data = {
            "test_service": {
                "health_check": "test_health_command",
                "restart": "test_restart_command",
                "rebuild": "test_rebuild_command"
            },
            "another_service": {
                "health_check": "another_health_command",
                "restart": "another_restart_command"
            }
        }
        
        # Write config to file
        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f)
        
        # Create JAPA instance with mocked command executor
        self.japa = JAPA(self.config_file)
        
        # Mock the command executor
        self.japa.command_executor.execute_command = MagicMock()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    def test_register_handler(self):
        """Test registering a handler."""
        handler = MagicMock()
        self.japa.register_handler(handler)
        self.assertIn(handler, self.japa.handlers)
    
    def test_register_handler_duplicate(self):
        """Test registering the same handler twice."""
        handler = MagicMock()
        self.japa.register_handler(handler)
        self.japa.register_handler(handler)
        self.assertEqual(self.japa.handlers.count(handler), 1)
    
    def test_unregister_handler(self):
        """Test unregistering a handler."""
        handler = MagicMock()
        self.japa.register_handler(handler)
        result = self.japa.unregister_handler(handler)
        self.assertTrue(result)
        self.assertNotIn(handler, self.japa.handlers)
    
    def test_unregister_handler_not_registered(self):
        """Test unregistering a handler that is not registered."""
        handler = MagicMock()
        result = self.japa.unregister_handler(handler)
        self.assertFalse(result)
    
    def test_notify_handlers(self):
        """Test notifying handlers."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        self.japa.register_handler(handler1)
        self.japa.register_handler(handler2)
        
        self.japa._notify_handlers("test_service", True, "Test message")
        
        handler1.assert_called_with("test_service", True, "Test message")
        handler2.assert_called_with("test_service", True, "Test message")
    
    def test_notify_handlers_exception(self):
        """Test notifying handlers with one that raises an exception."""
        handler1 = MagicMock()
        handler2 = MagicMock(side_effect=Exception("Test exception"))
        handler3 = MagicMock()
        
        self.japa.register_handler(handler1)
        self.japa.register_handler(handler2)
        self.japa.register_handler(handler3)
        
        # This should not raise an exception
        self.japa._notify_handlers("test_service", True, "Test message")
        
        handler1.assert_called_with("test_service", True, "Test message")
        handler2.assert_called_with("test_service", True, "Test message")
        handler3.assert_called_with("test_service", True, "Test message")
    
    def test_check_health_all_services(self):
        """Test checking health of all services."""
        # Configure mock return values
        self.japa.command_executor.execute_command.side_effect = [
            (True, "Service is healthy"),
            (False, "Service is unhealthy")
        ]
        
        results = self.japa.check_health()
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results["test_service"], (True, "Service is healthy"))
        self.assertEqual(results["another_service"], (False, "Service is unhealthy"))
        
        # Check service status was updated
        self.assertEqual(self.japa.service_status["test_service"], True)
        self.assertEqual(self.japa.service_status["another_service"], False)
    
    def test_check_health_specific_service(self):
        """Test checking health of a specific service."""
        # Configure mock return value
        self.japa.command_executor.execute_command.return_value = (True, "Service is healthy")
        
        results = self.japa.check_health("test_service")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results["test_service"], (True, "Service is healthy"))
        
        # Check service status was updated
        self.assertEqual(self.japa.service_status["test_service"], True)
    
    def test_check_health_no_command(self):
        """Test checking health of a service with no health check command."""
        # Add a service with no health check command
        self.japa.config.config["no_health_service"] = {}
        
        results = self.japa.check_health("no_health_service")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results["no_health_service"][0], False)
        self.assertIn("No health check command configured", results["no_health_service"][1])
    
    def test_restart_service(self):
        """Test restarting a service."""
        # Configure mock return value
        self.japa.command_executor.execute_command.return_value = (True, "Service restarted")
        
        success, message = self.japa.restart_service("test_service")
        
        self.assertTrue(success)
        self.assertEqual(message, "Service restarted")
        self.japa.command_executor.execute_command.assert_called_with("test_restart_command")
    
    def test_restart_service_no_command(self):
        """Test restarting a service with no restart command."""
        success, message = self.japa.restart_service("non_existent_service")
        
        self.assertFalse(success)
        self.assertIn("No restart command configured", message)
        self.japa.command_executor.execute_command.assert_not_called()
    
    def test_rebuild_service(self):
        """Test rebuilding a service."""
        # Configure mock return value
        self.japa.command_executor.execute_command.return_value = (True, "Service rebuilt")
        
        success, message = self.japa.rebuild_service("test_service")
        
        self.assertTrue(success)
        self.assertEqual(message, "Service rebuilt")
        self.japa.command_executor.execute_command.assert_called_with("test_rebuild_command")
    
    def test_rebuild_service_no_command(self):
        """Test rebuilding a service with no rebuild command."""
        success, message = self.japa.rebuild_service("another_service")
        
        self.assertFalse(success)
        self.assertIn("No rebuild command configured", message)
        self.japa.command_executor.execute_command.assert_not_called()
    
    def test_get_service_status(self):
        """Test getting service status."""
        # Set some status
        self.japa.service_status = {
            "test_service": True,
            "another_service": False
        }
        
        self.assertTrue(self.japa.get_service_status("test_service"))
        self.assertFalse(self.japa.get_service_status("another_service"))
        self.assertIsNone(self.japa.get_service_status("non_existent_service"))
    
    def test_get_all_services_status(self):
        """Test getting all services status."""
        # Set some status
        expected_status = {
            "test_service": True,
            "another_service": False
        }
        self.japa.service_status = expected_status.copy()
        
        self.assertEqual(self.japa.get_all_services_status(), expected_status)
    
    @patch("threading.Thread")
    def test_start_health_monitoring(self, mock_thread):
        """Test starting health monitoring."""
        self.japa.start_health_monitoring()
        
        self.assertTrue(self.japa.monitoring_running)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    @patch("threading.Thread")
    def test_start_health_monitoring_already_running(self, mock_thread):
        """Test starting health monitoring when already running."""
        self.japa.monitoring_running = True
        self.japa.start_health_monitoring()
        
        mock_thread.assert_not_called()
    
    @patch("threading.Thread")
    def test_stop_health_monitoring(self, mock_thread):
        """Test stopping health monitoring."""
        self.japa.monitoring_running = True
        self.japa.monitoring_thread = mock_thread.return_value
        
        self.japa.stop_health_monitoring()
        
        self.assertFalse(self.japa.monitoring_running)
        mock_thread.return_value.join.assert_called_once()
        self.assertIsNone(self.japa.monitoring_thread)
    
    @patch("threading.Thread")
    def test_stop_health_monitoring_not_running(self, mock_thread):
        """Test stopping health monitoring when not running."""
        self.japa.monitoring_running = False
        self.japa.monitoring_thread = None
        
        self.japa.stop_health_monitoring()
        
        self.assertFalse(self.japa.monitoring_running)


if __name__ == "__main__":
    unittest.main() 