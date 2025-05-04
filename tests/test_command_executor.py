"""
Unit tests for CommandExecutor class.
"""
import unittest
from unittest.mock import patch

from japa.command_executor import CommandExecutor


class TestCommandExecutor(unittest.TestCase):
    """Test cases for CommandExecutor class."""
    
    def test_execute_command_empty(self):
        """Test executing an empty command."""
        success, message = CommandExecutor.execute_command("")
        self.assertFalse(success)
        self.assertEqual(message, "No command specified")
    
    def test_execute_command_none(self):
        """Test executing a None command."""
        success, message = CommandExecutor.execute_command(None)
        self.assertFalse(success)
        self.assertEqual(message, "No command specified")
    
    @patch("subprocess.run")
    def test_execute_command_success(self, mock_run):
        """Test executing a command successfully."""
        # Configure the mock
        mock_process = mock_run.return_value
        mock_process.returncode = 0
        mock_process.stdout = "Command output"
        mock_process.stderr = ""
        
        # Execute command
        success, message = CommandExecutor.execute_command("echo 'test'")
        
        # Verify
        self.assertTrue(success)
        self.assertEqual(message, "Command output")
        mock_run.assert_called_once()
    
    @patch("subprocess.run")
    def test_execute_command_failure(self, mock_run):
        """Test executing a command that fails."""
        # Configure the mock
        mock_process = mock_run.return_value
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Command error"
        
        # Execute command
        success, message = CommandExecutor.execute_command("invalid_command")
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(message, "Error (code 1): Command error")
        mock_run.assert_called_once()
    
    @patch("subprocess.run")
    def test_execute_command_exception(self, mock_run):
        """Test executing a command that raises an exception."""
        # Configure the mock to raise an exception
        mock_run.side_effect = Exception("Test exception")
        
        # Execute command
        success, message = CommandExecutor.execute_command("problematic_command")
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(message, "Exception executing command: Test exception")
        mock_run.assert_called_once()
    
    @patch("subprocess.run")
    def test_execute_command_timeout(self, mock_run):
        """Test executing a command that times out."""
        # Configure the mock to raise a timeout exception
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired(cmd="test_command", timeout=300)
        
        # Execute command
        success, message = CommandExecutor.execute_command("slow_command")
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(message, "Command timed out after 5 minutes")
        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main() 