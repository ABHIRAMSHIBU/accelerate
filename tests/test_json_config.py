"""
Unit tests for JsonConfig class.
"""
import json
import os
import tempfile
import unittest

from japa.json_config import JsonConfig


class TestJsonConfig(unittest.TestCase):
    """Test cases for JsonConfig class."""
    
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
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    def test_load_config(self):
        """Test loading configuration from file."""
        config = JsonConfig(self.config_file)
        self.assertEqual(config.get_config(), self.config_data)
    
    def test_load_config_file_not_exist(self):
        """Test loading configuration from non-existent file."""
        config = JsonConfig("non_existent_file.json")
        self.assertEqual(config.get_config(), {})
    
    def test_get_service_config(self):
        """Test getting configuration for a specific service."""
        config = JsonConfig(self.config_file)
        service_config = config.get_service_config("test_service")
        self.assertEqual(service_config, self.config_data["test_service"])
    
    def test_get_service_config_not_exist(self):
        """Test getting configuration for a non-existent service."""
        config = JsonConfig(self.config_file)
        service_config = config.get_service_config("non_existent_service")
        self.assertIsNone(service_config)
    
    def test_get_services(self):
        """Test getting list of configured services."""
        config = JsonConfig(self.config_file)
        services = config.get_services()
        self.assertSetEqual(set(services), {"test_service", "another_service"})
    
    def test_get_health_check_command(self):
        """Test getting health check command for a service."""
        config = JsonConfig(self.config_file)
        command = config.get_health_check_command("test_service")
        self.assertEqual(command, "test_health_command")
    
    def test_get_health_check_command_not_exist(self):
        """Test getting health check command for a non-existent service."""
        config = JsonConfig(self.config_file)
        command = config.get_health_check_command("non_existent_service")
        self.assertIsNone(command)
    
    def test_get_restart_command(self):
        """Test getting restart command for a service."""
        config = JsonConfig(self.config_file)
        command = config.get_restart_command("test_service")
        self.assertEqual(command, "test_restart_command")
    
    def test_get_restart_command_not_exist(self):
        """Test getting restart command for a non-existent service."""
        config = JsonConfig(self.config_file)
        command = config.get_restart_command("non_existent_service")
        self.assertIsNone(command)
    
    def test_get_rebuild_command(self):
        """Test getting rebuild command for a service."""
        config = JsonConfig(self.config_file)
        command = config.get_rebuild_command("test_service")
        self.assertEqual(command, "test_rebuild_command")
    
    def test_get_rebuild_command_not_exist(self):
        """Test getting rebuild command for a non-existent service."""
        config = JsonConfig(self.config_file)
        command = config.get_rebuild_command("non_existent_service")
        self.assertIsNone(command)
    
    def test_get_rebuild_command_not_configured(self):
        """Test getting rebuild command for a service without rebuild configured."""
        config = JsonConfig(self.config_file)
        command = config.get_rebuild_command("another_service")
        self.assertIsNone(command)


if __name__ == "__main__":
    unittest.main() 