# JAPA - Just Another Project Automation

JAPA is a Python Telegram bot that monitors the health of services on a server and allows you to control them through Telegram.

## Features

- Monitor service health automatically
- Receive notifications when services become unhealthy
- Restart or rebuild services via Telegram commands
- Get status updates for all your services
- Easy configuration via JSON

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/japa.git
cd japa
```

2. Install the package:

```bash
pip install -e .
```

3. Create a configuration file (see `config.json` for an example)

4. Get a Telegram bot token from [@BotFather](https://t.me/BotFather)

## Usage

Run the bot with:

```bash
python src/main.py --config /path/to/config.json --token YOUR_TELEGRAM_TOKEN
```

Or set the token as an environment variable:

```bash
export JAPA_TELEGRAM_TOKEN=YOUR_TELEGRAM_TOKEN
python src/main.py --config /path/to/config.json
```

## Telegram Commands

- `/start` - Start receiving notifications
- `/stop` - Stop receiving notifications
- `/status [service]` - Get status of all services or a specific service
- `/list` - List all configured services
- `/restart service` - Restart a service
- `/rebuild service` - Rebuild a service
- `/help` - Display all available commands

## Configuration

Create a `config.json` file with your services:

```json
{
    "service_name": {
        "health_check": "command to check service health",
        "restart": "command to restart service",
        "rebuild": "command to rebuild service"
    }
}
```

Example:

```json
{
    "nextcloud": {
        "health_check": "curl -sf http://localhost:8080/status.php > /dev/null",
        "restart": "podman restart nextcloud",
        "rebuild": "cd /mnt/nas/nextcloud && podman compose pull && podman compose up -d --force-recreate"
    }
}
```

## Requirements

- Python 3.7+
- python-telegram-bot 20.0+ 