"""
CommandExecutor class for executing system commands.
"""
import subprocess
from typing import Tuple, Optional
import os


class CommandExecutor:
    """
    Executes shell commands and handles errors.
    """
    
    @staticmethod
    def execute_command(command: str) -> Tuple[bool, str]:
        """
        Execute a shell command and return the result.
        
        Args:
            command: The command to execute
            
        Returns:
            Tuple[bool, str]: A tuple containing success status and output/error message
        """
        if not command:
            return False, "No command specified"
        
        try:
            # Execute the command and capture output
            result = subprocess.run(
                command,
                shell=True,
                check=False,  # Don't raise exception on non-zero exit code
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, f"Error (code {result.returncode}): {result.stderr.strip()}"
        
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 5 minutes"
        
        except Exception as e:
            return False, f"Exception executing command: {str(e)}" 