# JAPA Installation Guide

JAPA (Just Another Process Assistant) is a Telegram bot that helps you monitor and manage services on your server. This guide will help you install and configure JAPA on your system.

## Prerequisites

- Linux system with systemd
- Python 3.x
- Git
- Root/sudo access
- Telegram Bot Token (Get it from [@BotFather](https://t.me/BotFather))
- Your Telegram User ID (Get it from [@userinfobot](https://t.me/userinfobot))

## Installation

### Quick Install

1. Clone the repository:
   ```bash
   git clone https://github.com/ABHIRAMSHIBU/accelerate.git
   cd accelerate
   ```

2. Run the installer as root:
   ```bash
   sudo bash install.sh
   ```

3. Follow the interactive prompts:
   - Choose between creating a dedicated service user (recommended) or using an existing user
   - Enter your Telegram Bot Token
   - Enter your Telegram User ID for superadmin access

The installer will:
- Set up the required directories
- Create a Python virtual environment
- Install dependencies
- Configure systemd service
- Set up secure permissions
- Start the service

### Installation Locations

- Application: `/opt/japa`
- Configuration: `/etc/japa`
- Data: `/var/lib/japa`

### Configuration Files

After installation, you'll find these configuration files:

1. `/etc/japa/config.json`: Service configurations
   ```json
   {
     "example_service": {
       "health_check": "echo 'Service is healthy'",
       "restart": "echo 'Restarting service'",
       "rebuild": "echo 'Rebuilding service'"
     }
   }
   ```

2. `/etc/japa/telegram_config.json`: Bot settings
   ```json
   {
     "db_path": "/var/lib/japa/users.db",
     "superadmin_ids": [your_telegram_id],
     "webhook": {
       "use_webhook": false,
       "webhook_url": "",
       "webhook_port": 8443,
       "cert_path": ""
     }
   }
   ```

## Security

The installer sets up secure file permissions:
- Configuration directory: `750 (drwxr-x---)`
- Config files: `640 (rw-r-----)`
- Telegram token: `600 (rw-------)`
- Data directory: `750 (drwxr-x---)`
- Database file: `640 (rw-r-----)`

Only root and the service user can access the configuration files.

## Managing the Service

### System-level service:
```bash
# Start the service
sudo systemctl start japa

# Stop the service
sudo systemctl stop japa

# Check status
sudo systemctl status japa

# View logs
sudo journalctl -u japa
```

### User-level service:
```bash
# Start the service
systemctl --user start japa

# Stop the service
systemctl --user stop japa

# Check status
systemctl --user status japa

# View logs
journalctl --user -u japa
```

## Updating JAPA

To update JAPA, run the installer again:
```bash
sudo bash install.sh
```

The installer will:
- Detect the existing installation
- Offer to backup your configurations
- Update the application while preserving your settings
- Restart the service

## Uninstalling

To uninstall JAPA:
```bash
sudo bash install.sh --uninstall
```

This will:
- Stop and disable the service
- Offer to backup your configurations and data
- Remove all JAPA files and directories
- Remove the service user (if created during installation)

## Troubleshooting

1. Check service status:
   ```bash
   sudo systemctl status japa
   ```

2. View logs:
   ```bash
   sudo journalctl -u japa -f
   ```

3. Check file permissions:
   ```bash
   ls -l /etc/japa/
   ls -l /var/lib/japa/
   ```

4. Verify configuration:
   ```bash
   ls -l /etc/japa/config.json
   ls -l /etc/japa/telegram_config.json
   ```

For more detailed configuration and usage instructions, please refer to the [README.md](README.md) and [docs/](docs/) directory.
