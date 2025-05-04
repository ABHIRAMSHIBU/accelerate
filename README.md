# JAPA - Just Another Process Assistant

JAPA is a service health monitoring and management bot that can check the status of various services, notify users of outages, and allow admins to restart or rebuild services when necessary.

## Features

- **Health Monitoring**: Automatically check the status of configured services
- **Notifications**: Alert users when a service becomes unhealthy
- **Service Management**: Restart or rebuild services via simple commands (admin only)
- **User Management**: Role-based access control for commands
- **Multiple Interfaces**: Modular design allows for multiple UI interfaces (currently Telegram)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/server_health_bot.git
cd server_health_bot
```

2. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure the bot (see Configuration section below)

## Configuration

JAPA uses two separate configuration files:

### 1. JAPA Configuration (`config.json`)

This file contains service-specific configurations:

```json
{
  "immich": {
    "health_check": {
      "url": "http://localhost:3001/api/server-info/ping",
      "timeout": 5,
      "interval": 60
    },
    "restart_command": "docker-compose -f /home/user/immich/docker-compose.yml restart",
    "rebuild_command": "docker-compose -f /home/user/immich/docker-compose.yml up -d --build"
  },
  "jellyfin": {
    "health_check": {
      "url": "http://localhost:8096/health",
      "timeout": 5,
      "interval": 60
    },
    "restart_command": "systemctl restart jellyfin",
    "rebuild_command": null
  }
}
```

### 2. Telegram Interface Configuration (`telegram_config.json`)

This file contains Telegram-specific configurations:

```json
{
  "token": "YOUR_TELEGRAM_BOT_TOKEN",
  "db_path": "users.db",
  "superadmin_ids": [123456789],
  "webhook": {
    "use_webhook": false,
    "webhook_url": "",
    "webhook_port": 8443,
    "cert_path": ""
  }
}
```

## Usage

### Starting the Bot

Basic usage with polling mode:

```bash
python src/main.py
```

With command line options:

```bash
python src/main.py --config config.json --telegram-config telegram_config.json --debug
```

Using webhook mode:

```bash
python src/main.py --webhook --webhook-url https://example.com:8443
```

### Telegram Bot Commands

#### Available to All Users

- `/start` - Start receiving notifications
- `/stop` - Stop receiving notifications
- `/status [service]` - Check status of all services or a specific service
- `/list` - List all configured services
- `/help` - Show available commands
- `/requestadmin [reason]` - Request admin privileges (for regular users)

#### Admin Commands

- `/restart <service>` - Restart a specific service
- `/rebuild <service>` - Rebuild a specific service

#### Superadmin Commands

- `/admins` - List all admins
- `/promote <user_id>` - Promote a user to admin
- `/demote <user_id>` - Demote an admin to regular user
- `/remove <user_id>` - Remove a user completely from the database

## User Management CLI Tool

JAPA includes a command-line tool for managing users in the database:

```bash
# Make the script executable
chmod +x src/japa_admin.py

# List all users
./src/japa_admin.py users list

# Add a new user
./src/japa_admin.py users add 123456789 --username username --role admin

# Promote a user to admin
./src/japa_admin.py users promote 123456789

# Demote a user to regular
./src/japa_admin.py users demote 123456789

# Remove a user
./src/japa_admin.py users remove 123456789

# Export users to JSON
./src/japa_admin.py users export --format json

# List pending admin requests
./src/japa_admin.py requests list

# Approve a request
./src/japa_admin.py requests approve <request_id>

# Deny a request
./src/japa_admin.py requests deny <request_id>
```

## Architecture

JAPA follows a modular design with clear separation of concerns:

1. **Core JAPA Module** - Service health checking and management logic
2. **Interface Modules** - UI-specific code (currently Telegram)
3. **User Database** - Authentication and role management

This design allows JAPA to be extended to support multiple interfaces in the future, such as Discord, Slack, or a web UI.

## Command Line Arguments

```
usage: main.py [-h] [-c CONFIG] [--telegram-config TELEGRAM_CONFIG] [--token TOKEN] [--debug] [--webhook] [--webhook-url WEBHOOK_URL]
               [--webhook-port WEBHOOK_PORT] [--cert-path CERT_PATH] [--db-path DB_PATH] [--superadmin-id SUPERADMIN_ID]
               [--migrate-users MIGRATE_USERS]

JAPA Server Health Bot

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to JAPA config file
  --telegram-config TELEGRAM_CONFIG
                        Path to Telegram interface config file
  --token TOKEN         Telegram bot token (overrides config)
  --debug               Enable debug mode with extra logging
  --webhook             Use webhook instead of polling
  --webhook-url WEBHOOK_URL
                        Webhook URL (e.g., https://example.com:8443/TOKEN)
  --webhook-port WEBHOOK_PORT
                        Port for webhook server
  --cert-path CERT_PATH
                        Path to SSL certificate for webhook
  --db-path DB_PATH     Path to SQLite database file (overrides config)
  --superadmin-id SUPERADMIN_ID
                        Telegram user ID to be set as superadmin (can be specified multiple times, overrides config)
  --migrate-users MIGRATE_USERS
                        Migrate users from a JSON file to SQLite database
```

## Environment Variables

JAPA supports configuration via environment variables:

- `TELEGRAM_TOKEN` - Telegram bot token
- `JAPA_DB_PATH` - Path to SQLite database file
- `JAPA_SUPERADMIN_ID` - Comma-separated list of superadmin Telegram user IDs

## Development

### Adding a New Service

To add a new service, simply add a new entry to the `config.json` file with the appropriate health check URL and commands.

### Extending JAPA with New Interfaces

To add a new interface (e.g., Discord), create a new class similar to `TelegramInterface` that interacts with the JAPA core.

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 