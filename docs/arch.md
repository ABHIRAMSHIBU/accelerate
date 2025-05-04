# Just Another Project Automation (JAPA)
JAPA project is a Python Telegram bot that monitors the health of services on a server and allows for remote management through Telegram.

## Architecture

### Classes

- `JsonConfig` class:
    - Loads configuration from a JSON file
    - Provides methods to access specific service configurations
    - Retrieves health check, restart, and rebuild commands

- `TelegramBot` class:
    - Handles communication with the Telegram Bot API
    - Supports both polling mode and webhook mode for receiving updates
    - Manages command handlers and message sending
    - Provides robust error handling and reconnection logic

- `CommandExecutor` class:
    - Executes shell commands safely
    - Captures command output and error messages
    - Implements timeout handling for long-running commands

- `JAPA` class:
    - Core service monitoring engine
    - Integrates JsonConfig and CommandExecutor
    - Provides health checking, service restart, and rebuild capabilities
    - Implements the observer pattern for notifications
    - Runs background monitoring thread for periodic health checks

- `TelegramInterface` class:
    - Connects JAPA with Telegram
    - Manages user registration for notifications
    - Processes command requests from users
    - Dispatches notifications to registered users
    - Provides a complete command handler interface

### Class Diagram

```mermaid
classDiagram
    class JsonConfig {
        +load_config()
        +get_config()
        +get_services()
        +get_health_check_command()
        +get_restart_command()
        +get_rebuild_command()
    }
    class TelegramBot {
        +send_message()
        +broadcast_message()
        +register_command_handler()
        +start_bot(use_webhook, webhook_url)
        +stop_bot()
    }
    class CommandExecutor {
        +execute_command()
    }
    class JAPA {
        +check_health()
        +restart_service()
        +rebuild_service()
        +register_handler()
        +unregister_handler()
        +start_health_monitoring()
        +stop_health_monitoring()
        +get_all_services_status()
    }
    class TelegramInterface {
        +start(webhook_config)
        +stop()
        +register_user()
        +unregister_user()
        +notification_handler()
        +_handle_commands()
    }
    
    JsonConfig --> JAPA
    CommandExecutor --> JAPA
    JAPA --> TelegramInterface
    TelegramBot --> TelegramInterface
```

### System Flow

```mermaid
graph TD
    A[JsonConfig] --> B[JAPA]
    B --> C[CommandExecutor]
    C --> B
    B --> D[TelegramInterface]
    E[TelegramBot] --> D
    D --> B
    F[Webhook/Polling] --> E
```

## Configuration

JAPA uses a JSON configuration file to define services and their management commands:

```json
{
    "immich": {
        "health_check": "health_check_podman.sh immich_redis immich_machine_learning immich_postgres immich_server",
        "restart": "cd /mnt/nas/immich && podman compose up -d",
        "rebuild": "cd /mnt/nas/immich && podman compose pull && podman compose up -d --force-recreate"
    },
    "jellyfin": {
        "health_check": "health_check_podman.sh jellyfin",
        "restart": "podman restart jellyfin"
    }
}
```

Configuration for each service can include:
- `health_check`: Command to check service health
- `restart`: Command to restart the service
- `rebuild`: Command to rebuild/recreate the service

The Telegram token is provided separately via command line arguments or environment variables.

## Telegram Webhook vs Polling

### What is a Webhook?

A webhook is a mechanism where Telegram sends real-time updates to your bot by making HTTP requests to a URL you specify whenever there's a new message or event. It's a "push" approach rather than the "pull" approach of polling.

### Polling Mode

In polling mode, your bot repeatedly asks Telegram "Do you have any new messages for me?" This is simple but inefficient:

- Pros:
  - Easier to set up - no public server needed
  - Works behind firewalls and NATs
  - Simple to implement
- Cons:
  - Higher latency - messages processed in batches
  - Consumes more bandwidth and resources
  - Less efficient for bots with sporadic usage

### Webhook Mode

In webhook mode, Telegram directly notifies your bot when new messages arrive:

- Pros:
  - Real-time updates - lower latency
  - More efficient use of resources
  - Better for production environments
- Cons:
  - Requires a publicly accessible HTTPS server
  - Needs SSL certificate
  - More complex setup

### Using Webhooks with JAPA

To use webhook mode, you need:

1. A public-facing server with a valid SSL certificate
2. Open port (default: 8443)
3. Run JAPA with webhook parameters:

```bash
python src/main.py --config config.json --webhook --webhook-url https://your-server.com:8443
```

You can also specify a custom port and certificate path:

```bash
python src/main.py --config config.json --webhook --webhook-url https://your-server.com:8443 --webhook-port 8443 --cert-path /path/to/cert.pem
```

The JAPA bot will automatically handle setting up the webhook with Telegram and will fall back to polling mode if webhook setup fails.

## Features

### JsonConfig
- Parses and validates JSON configuration
- Provides typed access to configuration values
- Supports nested configuration for different services
- Handles missing configurations gracefully

### CommandExecutor
- Executes shell commands with proper error handling
- Captures stdout and stderr
- Implements timeout for command execution (5 minutes)
- Returns standardized result tuple (success, message)

### JAPA
- Health monitoring:
  - Checks service health via configured commands
  - Supports checking specific services or all services
  - Maintains status history
- Service management:
  - Restart services with proper error handling
  - Rebuild services with proper error handling
- Notification system:
  - Observer pattern for health status notifications
  - Register/unregister notification handlers
- Background monitoring:
  - Thread-based periodic health checking
  - Configurable check interval

### TelegramBot
- Messaging:
  - Send messages to individual users
  - Broadcast messages to multiple users
- Command handling:
  - Register command handlers
  - Process incoming commands
  - Handle unknown commands gracefully
- Connectivity:
  - Polling mode for simple deployments
  - Webhook mode for improved efficiency
  - Auto-fallback to polling if webhook setup fails
  - Proper error handling and reconnection logic

### TelegramInterface
- User management:
  - Registration/unregistration of users
  - Persistence of user data
- Command processing:
  - `/start` - Register for notifications
  - `/stop` - Unregister from notifications
  - `/status [service]` - Check service status
  - `/list` - List all configured services
  - `/restart <service>` - Restart a service
  - `/rebuild <service>` - Rebuild a service
  - `/help` - Show available commands
- Notification delivery:
  - Send health status notifications to registered users
  - Format messages for readability

## Running the Bot

JAPA supports two modes of operation:

### Polling Mode (Simple)
```bash
python src/main.py --config config.json --token YOUR_TELEGRAM_TOKEN
```

### Webhook Mode (Efficient)
```bash
python src/main.py --config config.json --token YOUR_TELEGRAM_TOKEN --webhook --webhook-url https://your-server.com:8443
```

Additional options:
- `--debug`: Enable debug logging
- `--webhook-port`: Set custom webhook port
- `--cert-path`: Path to SSL certificate

## Architecture Review

The JAPA system is designed with a clear separation of concerns, following modular design principles:

1. **Core Components**:
   - **JAPA**: Central engine that manages service health checks and operations
   - **JsonConfig**: Configuration management
   - **CommandExecutor**: Command execution layer
   - **TelegramBot**: Communication layer
   - **TelegramInterface**: User interface layer

2. **Key Design Patterns**:
   - **Observer Pattern**: JAPA uses handler registration for push notifications
   - **Facade Pattern**: JAPA acts as a simplified interface to complex subsystems
   - **Command Pattern**: CommandExecutor separates command execution from invocation
   - **Strategy Pattern**: Support for different update receiving strategies (polling/webhook)

3. **Strengths**:
   - Good separation of concerns
   - Extensible design (easy to add more services or notification methods)
   - Configurable via JSON (no code changes needed for new services)
   - Asynchronous health monitoring
   - Support for both polling and webhook modes
   - Comprehensive error handling and logging

4. **Areas for Future Enhancement**:
   - Metrics collection and visualization
   - More flexible notification filtering
   - Enhanced security and user authorization
   - Service-specific custom commands
   - Support for service dependencies

Overall, the architecture provides a solid foundation for a service monitoring system. Its modular design allows for future extensions and maintenance while keeping components loosely coupled.
    
