"""
JsonConfig class for loading and accessing configuration from a JSON file.
"""
import json
import os
from typing import Dict, Any, Optional


class JsonConfig:
    """
    Loads the configuration from a JSON file and provides access methods.
    """
    
    def __init__(self, config_file: str):
        """
        Initialize the JsonConfig with a config file path.
        
        Args:
            config_file: Path to the JSON configuration file
        """
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load the configuration from the JSON file.
        
        Returns:
            bool: True if the configuration was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                return True
            else:
                print(f"Config file {self.config_file} does not exist.")
                return False
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the entire configuration.
        
        Returns:
            Dict: The entire configuration
        """
        return self.config
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, str]]:
        """
        Get the configuration for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dict or None: Service configuration or None if service doesn't exist
        """
        return self.config.get(service_name, None)
    
    def get_services(self) -> list:
        """
        Get a list of all configured services.
        
        Returns:
            list: List of service names
        """
        return list(self.config.keys())
    
    def get_health_check_command(self, service_name: str) -> Optional[str]:
        """
        Get the health check command for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            str or None: Health check command or None if not configured
        """
        service_config = self.get_service_config(service_name)
        if service_config:
            return service_config.get('health_check', None)
        return None
    
    def get_restart_command(self, service_name: str) -> Optional[str]:
        """
        Get the restart command for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            str or None: Restart command or None if not configured
        """
        service_config = self.get_service_config(service_name)
        if service_config:
            return service_config.get('restart', None)
        return None
    
    def get_rebuild_command(self, service_name: str) -> Optional[str]:
        """
        Get the rebuild command for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            str or None: Rebuild command or None if not configured
        """
        service_config = self.get_service_config(service_name)
        if service_config:
            return service_config.get('rebuild', None)
        return None 