"""
JAPA (Just Another Process Assistant) main class.
"""
import threading
import time
from typing import Dict, Callable, List, Any, Optional, Tuple

from .json_config import JsonConfig
from .command_executor import CommandExecutor


class JAPA:
    """
    Main class that manages service monitoring and operations.
    """
    
    def __init__(self, config_file: str):
        """
        Initialize the JAPA system.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config = JsonConfig(config_file)
        self.command_executor = CommandExecutor()
        self.handlers = []
        self.service_status = {}  # Store the last known status of each service
        self.monitoring_thread = None
        self.monitoring_running = False
    
    def register_handler(self, handler: Callable[[str, bool, str], None]) -> None:
        """
        Register a handler to receive notifications.
        
        Args:
            handler: A function that takes (service_name, status, message)
        """
        if handler not in self.handlers:
            self.handlers.append(handler)
    
    def unregister_handler(self, handler: Callable[[str, bool, str], None]) -> bool:
        """
        Unregister a handler.
        
        Args:
            handler: The handler to unregister
            
        Returns:
            bool: True if the handler was unregistered, False otherwise
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            return True
        return False
    
    def _notify_handlers(self, service_name: str, status: bool, message: str) -> None:
        """
        Notify all registered handlers.
        
        Args:
            service_name: Name of the service
            status: Status of the service (True = healthy, False = unhealthy)
            message: Message with details
        """
        for handler in self.handlers:
            try:
                handler(service_name, status, message)
            except Exception as e:
                print(f"Error calling handler: {str(e)}")
    
    def check_health(self, service_name: Optional[str] = None) -> Dict[str, Tuple[bool, str]]:
        """
        Check the health of services.
        
        Args:
            service_name: Name of a specific service to check, or None to check all
            
        Returns:
            Dict[str, Tuple[bool, str]]: Dictionary of service names to (status, message) tuples
        """
        results = {}
        
        # If service_name is provided, check only that service
        if service_name:
            services = [service_name]
        else:
            services = self.config.get_services()
        
        for service in services:
            command = self.config.get_health_check_command(service)
            if not command:
                results[service] = (False, f"No health check command configured for {service}")
                continue
            
            success, output = self.command_executor.execute_command(command)
            results[service] = (success, output)
            
            # Update service status
            self.service_status[service] = success
            
            # Notify handlers of status change
            self._notify_handlers(service, success, output)
        
        return results
    
    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Restart a service.
        
        Args:
            service_name: Name of the service to restart
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        command = self.config.get_restart_command(service_name)
        if not command:
            return False, f"No restart command configured for {service_name}"
        
        success, output = self.command_executor.execute_command(command)
        
        # Notify handlers
        self._notify_handlers(
            service_name, 
            success, 
            f"Service restart {'successful' if success else 'failed'}: {output}"
        )
        
        return success, output
    
    def rebuild_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Rebuild a service.
        
        Args:
            service_name: Name of the service to rebuild
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        command = self.config.get_rebuild_command(service_name)
        if not command:
            return False, f"No rebuild command configured for {service_name}"
        
        success, output = self.command_executor.execute_command(command)
        
        # Notify handlers
        self._notify_handlers(
            service_name, 
            success, 
            f"Service rebuild {'successful' if success else 'failed'}: {output}"
        )
        
        return success, output
    
    def get_service_status(self, service_name: str) -> Optional[bool]:
        """
        Get the last known status of a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            bool or None: True if healthy, False if unhealthy, None if unknown
        """
        return self.service_status.get(service_name, None)
    
    def get_all_services_status(self) -> Dict[str, Optional[bool]]:
        """
        Get the status of all services.
        
        Returns:
            Dict[str, Optional[bool]]: Dictionary of service names to their status
        """
        return self.service_status
    
    def _health_check_loop(self, interval: int = 10) -> None:
        """
        Background loop to periodically check service health.
        
        Args:
            interval: Interval in seconds between health checks
        """
        while self.monitoring_running:
            self.check_health()
            time.sleep(interval)
    
    def start_health_monitoring(self, interval: int = 10) -> None:
        """
        Start the background health monitoring thread.
        
        Args:
            interval: Interval in seconds between health checks
        """
        if not self.monitoring_running:
            self.monitoring_running = True
            self.monitoring_thread = threading.Thread(
                target=self._health_check_loop,
                args=(interval,),
                daemon=True
            )
            self.monitoring_thread.start()
    
    def stop_health_monitoring(self) -> None:
        """
        Stop the background health monitoring thread.
        """
        self.monitoring_running = False
        if self.monitoring_thread:
            # Just set the flag, thread will exit on next loop
            self.monitoring_thread.join(timeout=15)
            self.monitoring_thread = None 