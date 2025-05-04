#!/usr/bin/env python3
"""
Main entry point for the JAPA Server Health Bot
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Any, Union

from japa.json_config import JsonConfig
from japa.japa import JAPA
from japa.telegram_interface import TelegramInterface

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="JAPA Server Health Bot")
    parser.add_argument(
        "-c", "--config", type=str, default="config.json", help="Path to JAPA config file"
    )
    parser.add_argument(
        "--telegram-config", type=str, default="telegram_config.json", 
        help="Path to Telegram interface config file"
    )
    parser.add_argument(
        "--token", type=str, help="Telegram bot token (overrides config)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with extra logging"
    )
    parser.add_argument(
        "--webhook", action="store_true", help="Use webhook instead of polling"
    )
    parser.add_argument(
        "--webhook-url", type=str, help="Webhook URL (e.g., https://example.com:8443/TOKEN)"
    )
    parser.add_argument(
        "--webhook-port", type=int, default=8443, help="Port for webhook server"
    )
    parser.add_argument(
        "--cert-path", type=str, help="Path to SSL certificate for webhook"
    )
    parser.add_argument(
        "--db-path", type=str, help="Path to SQLite database file (overrides config)"
    )
    parser.add_argument(
        "--superadmin-id", type=int, action="append", 
        help="Telegram user ID to be set as superadmin (can be specified multiple times, overrides config)"
    )
    parser.add_argument(
        "--migrate-users", type=str, help="Migrate users from a JSON file to SQLite database"
    )
    
    return parser.parse_args()


def load_telegram_config(config_path: str) -> Dict[str, Any]:
    """
    Load Telegram interface configuration from file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded Telegram configuration from {config_path}")
        return config
    except Exception as e:
        logger.warning(f"Failed to load Telegram config from {config_path}: {str(e)}")
        return {}


async def main() -> None:
    """
    Main entry point for the JAPA Server Health Bot.
    """
    args = parse_args()
    
    # Set debug mode if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Load JAPA config
    try:
        japa_config = JsonConfig(args.config)
        logger.info(f"Loaded JAPA configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load JAPA config: {str(e)}")
        sys.exit(1)
    
    # Load Telegram config
    telegram_config = load_telegram_config(args.telegram_config)
    
    # Get Telegram token from args, env var, or config
    telegram_token = args.token or os.environ.get("TELEGRAM_TOKEN") or telegram_config.get("token")
    
    # Check for required token
    if not telegram_token:
        logger.error("No Telegram token provided. Use --token argument, set TELEGRAM_TOKEN environment variable, or add token to telegram_config.json")
        sys.exit(1)
    else:
        logger.info(f"Using Telegram token: {telegram_token[:5]}...{telegram_token[-5:]}")
    
    # Get database path from args, env var, or config
    db_path = args.db_path or os.environ.get("JAPA_DB_PATH") or telegram_config.get("db_path", "users.db")
    logger.info(f"Using database path: {db_path}")
    
    # Get superadmin IDs from args, env var, or config
    superadmin_ids = []
    
    # From command line arguments
    if args.superadmin_id:
        superadmin_ids.extend(args.superadmin_id)
        logger.info(f"Added superadmin IDs from command line: {args.superadmin_id}")
    
    # From environment variables
    env_superadmin = os.environ.get("JAPA_SUPERADMIN_ID")
    if env_superadmin:
        try:
            # Support for comma-separated list of IDs
            for user_id in env_superadmin.split(","):
                superadmin_ids.append(int(user_id.strip()))
            logger.info(f"Added superadmin IDs from environment: {superadmin_ids}")
        except ValueError:
            logger.error(f"Invalid superadmin ID in environment variable: {env_superadmin}")
    
    # From config file
    if "superadmin_ids" in telegram_config and isinstance(telegram_config["superadmin_ids"], list):
        for user_id in telegram_config["superadmin_ids"]:
            if isinstance(user_id, int) and user_id not in superadmin_ids:
                superadmin_ids.append(user_id)
        logger.info(f"Added superadmin IDs from config: {telegram_config.get('superadmin_ids')}")
    
    if not superadmin_ids:
        logger.warning("No superadmin IDs provided. You won't be able to promote users to admin.")
    else:
        logger.info(f"Using superadmin IDs: {superadmin_ids}")
    
    # Webhook configuration (combine args and config)
    webhook_config = None
    if args.webhook or telegram_config.get("webhook", {}).get("use_webhook", False):
        # Start with webhook config from file
        webhook_config = telegram_config.get("webhook", {})
        
        # Override with command line arguments
        if args.webhook:
            webhook_config["use_webhook"] = True
        if args.webhook_url:
            webhook_config["webhook_url"] = args.webhook_url
        if args.webhook_port:
            webhook_config["webhook_port"] = args.webhook_port
        if args.cert_path:
            webhook_config["cert_path"] = args.cert_path
        
        # Check for required URL
        if not webhook_config.get("webhook_url"):
            logger.error("Webhook URL not provided. Use --webhook-url or add webhook_url to telegram_config.json")
            sys.exit(1)
        
        # If the webhook URL doesn't include the token, append it
        if not webhook_config["webhook_url"].endswith(telegram_token):
            if webhook_config["webhook_url"].endswith('/'):
                webhook_config["webhook_url"] += telegram_token
            else:
                webhook_config["webhook_url"] += '/' + telegram_token
        
        logger.info(f"Using webhook: {webhook_config['webhook_url']}")
    
    # Initialize the TelegramInterface
    try:
        # Migrate users from JSON if requested
        if args.migrate_users:
            from japa.user_database import UserDatabase
            logger.info(f"Migrating users from {args.migrate_users} to {db_path}")
            db = UserDatabase(db_path, debug=args.debug)
            num_migrated, num_failed = db.migrate_from_json(args.migrate_users)
            db.close()
            logger.info(f"Migration complete: {num_migrated} users migrated, {num_failed} failed")
        
        # Create a JAPA instance
        japa = JAPA(args.config)
        
        # Create a TelegramInterface instance
        telegram_interface = TelegramInterface(
            japa=japa,
            telegram_token=telegram_token,
            db_path=db_path,
            debug=args.debug,
            superadmin_ids=superadmin_ids
        )
        
        # Start the TelegramBot with webhook config if provided
        await telegram_interface.start(webhook_config=webhook_config)
        
        # Let the bot run indefinitely until interrupted
        logger.info("Bot is running. Press CTRL+C to stop.")
        while True:
            await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        # Clean shutdown
        try:
            await telegram_interface.stop()
            logger.info("Shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main()) 