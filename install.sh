#!/bin/bash

# install.sh for JAPA - Just Another Process Assistant
# This script installs JAPA as a systemd service with secure configuration

set -e  # Exit on any error

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default installation paths
INSTALL_DIR="/opt/japa"
CONFIG_DIR="/etc/japa"
DATA_DIR="/var/lib/japa"
DEFAULT_SERVICE_USER="japa_service"
SERVICE_USER=""
CURRENT_USER=$(whoami)
REINSTALL=false

# Banner
echo -e "${GREEN}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║                                           ║"
echo "  ║   JAPA - Just Another Process Assistant   ║"
echo "  ║              Installer Script             ║"
echo "  ║                                           ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run as root${NC}"
  exit 1
fi

# Parse command line arguments
ACTION="install"
while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall)
            ACTION="uninstall"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to uninstall JAPA
uninstall_japa() {
    echo -e "${YELLOW}Uninstalling JAPA...${NC}"
    
    # Stop and disable service if it exists
    if systemctl is-active --quiet japa.service; then
        echo "Stopping JAPA service..."
        systemctl stop japa.service
    fi
    if systemctl is-enabled --quiet japa.service; then
        echo "Disabling JAPA service..."
        systemctl disable japa.service
    fi

    # Remove service files
    rm -f /etc/systemd/system/japa.service
    systemctl daemon-reload

    # Optionally backup config and data
    if confirm "Would you like to backup your configuration and data before removal?"; then
        BACKUP_DIR="/tmp/japa_backup_$(date +%Y%m%d%H%M%S)"
        echo -e "${YELLOW}Backing up to ${BACKUP_DIR}...${NC}"
        mkdir -p "$BACKUP_DIR"
        [ -d "$CONFIG_DIR" ] && cp -r "$CONFIG_DIR" "$BACKUP_DIR/"
        [ -d "$DATA_DIR" ] && cp -r "$DATA_DIR" "$BACKUP_DIR/"
    fi

    # Remove directories
    rm -rf "$INSTALL_DIR"
    rm -rf "$CONFIG_DIR"
    rm -rf "$DATA_DIR"

    # Remove user if it was created by us
    if [ "$SERVICE_USER" = "$DEFAULT_SERVICE_USER" ]; then
        if id "$SERVICE_USER" &>/dev/null; then
            userdel "$SERVICE_USER"
            echo "Removed service user $SERVICE_USER"
        fi
    fi

    echo -e "${GREEN}JAPA has been uninstalled successfully.${NC}"
    if [ ! -z "$BACKUP_DIR" ]; then
        echo -e "${YELLOW}Your backup is available at: ${BACKUP_DIR}${NC}"
    fi
    exit 0
}

# Handle uninstall if requested
if [ "$ACTION" = "uninstall" ]; then
    uninstall_japa
fi

# Function to prompt for confirmation
confirm() {
    read -p "$1 [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to check for existing installation
check_existing_installation() {
    if [ -d "$INSTALL_DIR" ] || [ -d "$CONFIG_DIR" ] || [ -d "$DATA_DIR" ] || [ -f "/etc/systemd/system/japa.service" ]; then
        echo -e "${YELLOW}Existing JAPA installation detected.${NC}"
        if confirm "Would you like to reinstall JAPA?"; then
            REINSTALL=true
            echo -e "${BLUE}Reinstallation mode activated.${NC}"
            
            # Try to determine current service user if service exists
            if [ -f "/etc/systemd/system/japa.service" ]; then
                CURRENT_SERVICE_USER=$(grep "^User=" /etc/systemd/system/japa.service | cut -d= -f2)
                if [ ! -z "$CURRENT_SERVICE_USER" ]; then
                    echo -e "${BLUE}Current service is running as user: ${CURRENT_SERVICE_USER}${NC}"
                    if confirm "Would you like to keep using this user?"; then
                        SERVICE_USER="$CURRENT_SERVICE_USER"
                    fi
                fi
            fi
            
            # Check if token exists and offer to reuse it
            if [ -f "$CONFIG_DIR/japa.env" ]; then
                EXISTING_TOKEN=$(grep "^TELEGRAM_TOKEN=" "$CONFIG_DIR/japa.env" | cut -d= -f2)
                if [ ! -z "$EXISTING_TOKEN" ]; then
                    if confirm "Would you like to reuse your existing Telegram bot token?"; then
                        TOKEN="$EXISTING_TOKEN"
                        echo -e "${BLUE}Using existing token.${NC}"
                    fi
                fi
            fi
            
            # Check if superadmin ID exists and offer to reuse it
            if [ -f "$CONFIG_DIR/telegram_config.json" ]; then
                EXISTING_SUPERADMIN=$(grep -o '"superadmin_ids": \[[^]]*\]' "$CONFIG_DIR/telegram_config.json" | grep -o '[0-9]*')
                if [ ! -z "$EXISTING_SUPERADMIN" ]; then
                    echo -e "${BLUE}Current superadmin ID: ${EXISTING_SUPERADMIN}${NC}"
                    if confirm "Would you like to keep this superadmin ID?"; then
                        SUPERADMIN_ID="$EXISTING_SUPERADMIN"
                        echo -e "${BLUE}Using existing superadmin ID.${NC}"
                    fi
                fi
            fi
            
            # Stop existing service if running
            if systemctl is-active --quiet japa.service; then
                echo -e "${YELLOW}Stopping existing JAPA service...${NC}"
                systemctl stop japa.service
            fi
            
            # Disable existing service
            if systemctl is-enabled --quiet japa.service; then
                echo -e "${YELLOW}Disabling existing JAPA service...${NC}"
                systemctl disable japa.service
            fi
            
            # Backup existing configuration if requested
            if [ -d "$CONFIG_DIR" ] && confirm "Would you like to backup your existing configuration?"; then
                BACKUP_DIR="/tmp/japa_backup_$(date +%Y%m%d%H%M%S)"
                echo -e "${YELLOW}Backing up configuration to ${BACKUP_DIR}...${NC}"
                mkdir -p "$BACKUP_DIR"
                cp -r "$CONFIG_DIR"/* "$BACKUP_DIR"/
                echo -e "${GREEN}Configuration backed up successfully.${NC}"
            fi
            
            # Backup existing database if requested
            if [ -f "$DATA_DIR/users.db" ] && confirm "Would you like to backup your existing user database?"; then
                BACKUP_DB="/tmp/japa_users_$(date +%Y%m%d%H%M%S).db"
                echo -e "${YELLOW}Backing up database to ${BACKUP_DB}...${NC}"
                cp "$DATA_DIR/users.db" "$BACKUP_DB"
                echo -e "${GREEN}Database backed up successfully.${NC}"
            fi
        else
            echo -e "${RED}Installation aborted.${NC}"
            exit 0
        fi
    fi
}

# Function to prompt for service user
select_service_user() {
    if [ -z "$SERVICE_USER" ]; then
        echo -e "${YELLOW}JAPA can run as a dedicated service user or as an existing user.${NC}"
        echo "Options:"
        echo "  1) Create a dedicated service user ($DEFAULT_SERVICE_USER) [recommended]"
        echo "  2) Run as a specific existing user"
        
        read -p "Select an option [1-2]: " user_option
        case $user_option in
            1)
                SERVICE_USER="$DEFAULT_SERVICE_USER"
                echo -e "${BLUE}Selected dedicated service user: $SERVICE_USER${NC}"
                ;;
            2)
                read -p "Enter the username to run JAPA as: " custom_user
                if id "$custom_user" &>/dev/null; then
                    SERVICE_USER="$custom_user"
                    echo -e "${BLUE}Selected existing user: $SERVICE_USER${NC}"
                else
                    echo -e "${RED}Error: User $custom_user does not exist${NC}"
                    select_service_user
                fi
                ;;
            *)
                echo -e "${RED}Invalid option. Please try again.${NC}"
                select_service_user
                ;;
        esac
    fi
}

# Function to prompt for Telegram bot token
get_token() {
    if [ -z "$TOKEN" ]; then
        read -sp "Enter your Telegram bot token: " TOKEN
        echo
        if [ -z "$TOKEN" ]; then
            echo -e "${RED}Error: Token cannot be empty${NC}"
            get_token
        fi
    fi
}

# Function to prompt for superadmin ID
get_superadmin_id() {
    if [ -z "$SUPERADMIN_ID" ]; then
        read -p "Enter your Telegram user ID for superadmin access: " SUPERADMIN_ID
        if [ -z "$SUPERADMIN_ID" ]; then
            echo -e "${RED}Error: Superadmin ID cannot be empty${NC}"
            get_superadmin_id
        fi
    fi
}

# Function to create system user if needed
create_user() {
    if [ "$SERVICE_USER" = "$DEFAULT_SERVICE_USER" ]; then
        echo -e "${YELLOW}Creating system user for JAPA...${NC}"
        if id "$SERVICE_USER" &>/dev/null; then
            echo "User $SERVICE_USER already exists"
        else
            useradd -r -s /bin/false "$SERVICE_USER"
            echo "Created user $SERVICE_USER"
        fi
    else
        echo -e "${BLUE}Using existing user: $SERVICE_USER${NC}"
    fi
}

# Function to set up directories
setup_directories() {
    echo -e "${YELLOW}Setting up directories...${NC}"
    
    # Create directories if they don't exist
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    
    echo "Created/verified directories:"
    echo "  - $INSTALL_DIR (application)"
    echo "  - $CONFIG_DIR (configuration)"
    echo "  - $DATA_DIR (data)"
}

# Function to clone the repository
clone_repository() {
    echo -e "${YELLOW}Cloning JAPA repository...${NC}"
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Repository already exists, updating..."
        cd "$INSTALL_DIR"
        git pull
    else
        git clone https://github.com/ABHIRAMSHIBU/accelerate.git "$INSTALL_DIR"
    fi
}

# Function to set up Python virtual environment
setup_venv() {
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
    cd "$INSTALL_DIR"
    
    # Remove existing venv if reinstalling
    if [ "$REINSTALL" = true ] && [ -d "$INSTALL_DIR/venv" ]; then
        echo "Removing existing virtual environment..."
        rm -rf "$INSTALL_DIR/venv"
    fi
    
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
}

# Function to create configuration files
create_config_files() {
    echo -e "${YELLOW}Setting up configuration files...${NC}"
    
    # Create config directory with secure permissions
    mkdir -p "$CONFIG_DIR"
    chmod 750 "$CONFIG_DIR"
    
    # Handle config.json
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        echo -e "${YELLOW}Creating new config.json template${NC}"
        cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "example_service": {
    "health_check": "echo 'Service is healthy'",
    "restart": "echo 'Restarting service'",
    "rebuild": "echo 'Rebuilding service'"
  }
}
EOF
        chmod 640 "$CONFIG_DIR/config.json"
        echo "Created template config.json - please edit with your actual services"
    else
        echo "config.json exists, preserving current configuration"
    fi
    
    # Handle telegram_config.json
    if [ ! -f "$CONFIG_DIR/telegram_config.json" ]; then
        echo -e "${YELLOW}Creating new telegram_config.json${NC}"
        cat > "$CONFIG_DIR/telegram_config.json" << EOF
{
  "db_path": "$DATA_DIR/users.db",
  "superadmin_ids": [$SUPERADMIN_ID],
  "webhook": {
    "use_webhook": false,
    "webhook_url": "",
    "webhook_port": 8443,
    "cert_path": ""
  }
}
EOF
        chmod 640 "$CONFIG_DIR/telegram_config.json"
        echo "Created telegram_config.json"
    else
        echo "telegram_config.json exists, preserving current configuration"
        # Update superadmin ID if it's a new one
        if [ ! -z "$SUPERADMIN_ID" ]; then
            if ! grep -q "$SUPERADMIN_ID" "$CONFIG_DIR/telegram_config.json"; then
                echo -e "${YELLOW}Adding new superadmin ID to existing config${NC}"
                sed -i "s/\"superadmin_ids\":\s*\[[^]]*\]/\"superadmin_ids\": [$SUPERADMIN_ID]/" "$CONFIG_DIR/telegram_config.json"
            fi
        fi
    fi
    
    # Handle environment file with token
    if [ ! -f "$CONFIG_DIR/japa.env" ]; then
        echo -e "${YELLOW}Creating new japa.env${NC}"
        echo "TELEGRAM_TOKEN=$TOKEN" > "$CONFIG_DIR/japa.env"
        chmod 600 "$CONFIG_DIR/japa.env"
        echo "Created japa.env with your bot token"
    elif [ ! -z "$TOKEN" ] && [ "$TOKEN" != "$(grep -oP '^TELEGRAM_TOKEN=\K.*' "$CONFIG_DIR/japa.env")" ]; then
        echo -e "${YELLOW}Updating Telegram token in existing japa.env${NC}"
        echo "TELEGRAM_TOKEN=$TOKEN" > "$CONFIG_DIR/japa.env"
    else
        echo "japa.env exists, preserving current configuration"
    fi
    
    # Create data directory with secure permissions
    mkdir -p "$DATA_DIR"
    chmod 750 "$DATA_DIR"
    
    # Create empty database file if it doesn't exist
    if [ ! -f "$DATA_DIR/users.db" ] || [ "$REINSTALL" = true ] && [ ! -f "$BACKUP_DB" ]; then
        touch "$DATA_DIR/users.db"
        chmod 640 "$DATA_DIR/users.db"
        echo "Created empty users database"
    elif [ "$REINSTALL" = true ] && [ -f "$BACKUP_DB" ]; then
        echo "Restoring users.db from backup..."
        cp "$BACKUP_DB" "$DATA_DIR/users.db"
        chmod 640 "$DATA_DIR/users.db"
    fi
}

# Function to create systemd service
create_systemd_service() {
    echo -e "${YELLOW}Creating systemd service...${NC}"
    
    # Determine if service should run as user or system level
    local service_type="system"
    local service_path="/etc/systemd/system/japa.service"
    
    if [ "$SERVICE_USER" != "$DEFAULT_SERVICE_USER" ]; then
        # Check if we should create a user-level service instead
        if confirm "Would you like to create a user-level systemd service instead of system-level?"; then
            service_type="user"
            mkdir -p "/home/$SERVICE_USER/.config/systemd/user/"
            service_path="/home/$SERVICE_USER/.config/systemd/user/japa.service"
        fi
    fi
    
    # Create the service file
    if [ "$service_type" = "system" ]; then
        cat > "$service_path" << EOF
[Unit]
Description=JAPA Service Health Monitoring Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/main.py --config $CONFIG_DIR/config.json --telegram-config $CONFIG_DIR/telegram_config.json
Restart=always
RestartSec=10
EnvironmentFile=$CONFIG_DIR/japa.env

# Security hardening
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true
ReadWritePaths=$DATA_DIR
#ProtectHome=true
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true

[Install]
WantedBy=multi-user.target
EOF
        echo "Created system-level systemd service file at $service_path"
    else
        cat > "$service_path" << EOF
[Unit]
Description=JAPA Service Health Monitoring Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/main.py --config $CONFIG_DIR/config.json --telegram-config $CONFIG_DIR/telegram_config.json
Restart=on-failure
RestartSec=10
EnvironmentFile=$CONFIG_DIR/japa.env

[Install]
WantedBy=default.target
EOF
        echo "Created user-level systemd service file at $service_path"
        chown "$SERVICE_USER":"$SERVICE_USER" "$service_path"
    fi
}

# Function to set proper ownership
set_ownership() {
    echo -e "${YELLOW}Setting proper file ownership...${NC}"
    
    # Set ownership for application files
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"
    
    # Set ownership for data directory
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$DATA_DIR"
    
    # Set ownership for config files - root:service_user with restricted permissions
    chown -R root:"$SERVICE_USER" "$CONFIG_DIR"
    
    # Ensure the service user can read but not modify sensitive files
    chmod 750 "$CONFIG_DIR"              # drwxr-x---
    chmod 640 "$CONFIG_DIR"/*.json       # -rw-r-----
    chmod 600 "$CONFIG_DIR/japa.env"     # -rw-------
    chmod 750 "$DATA_DIR"                # drwxr-x---
    chmod 640 "$DATA_DIR/users.db"       # -rw-r-----
    
    echo "File ownership and permissions set successfully"
}

# Main Installation Sequence
main() {
    # Check for existing installation first
    check_existing_installation

    # Get required information
    select_service_user
    get_token
    get_superadmin_id

    # Create system user if needed
    create_user

    # Setup application
    setup_directories
    clone_repository
    setup_venv

    # Create and secure configuration
    create_config_files
    create_systemd_service
    set_ownership

    # Start service
    echo -e "${YELLOW}Starting JAPA service...${NC}"
    if [ -f "/etc/systemd/system/japa.service" ]; then
        systemctl daemon-reload
        systemctl enable japa.service
        systemctl start japa.service
        echo -e "${GREEN}JAPA service has been enabled and started${NC}"
        systemctl status japa.service
    elif [ -f "/home/$SERVICE_USER/.config/systemd/user/japa.service" ]; then
        # For user-level service
        loginctl enable-linger "$SERVICE_USER"
        systemctl --user enable japa.service
        systemctl --user start japa.service
        echo -e "${GREEN}JAPA user service has been enabled and started${NC}"
        systemctl --user status japa.service
    fi

    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo -e "${YELLOW}Please check the configuration files in $CONFIG_DIR and modify them as needed.${NC}"
}

# Execute main installation sequence
main