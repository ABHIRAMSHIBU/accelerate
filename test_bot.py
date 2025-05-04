#!/usr/bin/env python3
"""
Simple test script for the JAPA service monitoring functionality.
"""
import os
import sys
import time

from src.japa.japa import JAPA

def notification_handler(service_name, status, message):
    """
    Simple notification handler that prints messages to the console.
    """
    status_text = "HEALTHY" if status else "UNHEALTHY"
    print(f"[{service_name}] {status_text}: {message}")

def main():
    """
    Main test function.
    """
    # Check if config file exists
    if not os.path.exists("config.json"):
        print("Error: config.json file not found.")
        sys.exit(1)
    
    # Create JAPA instance
    japa = JAPA("config.json")
    
    # Register notification handler
    japa.register_handler(notification_handler)
    
    # Check all services
    print("Checking all services...")
    results = japa.check_health()
    
    # Print results
    for service, (status, message) in results.items():
        status_text = "HEALTHY" if status else "UNHEALTHY"
        print(f"{service}: {status_text} - {message}")
    
    # Start health monitoring in background
    print("\nStarting health monitoring in background...")
    japa.start_health_monitoring(interval=5)
    
    try:
        # Keep running until interrupted
        print("Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopping health monitoring...")
    
    finally:
        # Stop health monitoring
        japa.stop_health_monitoring()
        print("Health monitoring stopped.")

if __name__ == "__main__":
    main() 