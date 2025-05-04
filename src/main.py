#!/usr/bin/env python3
"""
Main entry point for the JAPA Server Health Bot
"""
import argparse
import asyncio
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
        "-c", "--config", type=str, default="config.json", help="Path to config file"
    )
    parser.add_argument(
        "--token", type=str, help="Telegram bot token"
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
    
    return parser.parse_args()


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
    
    # Load config
    try:
        config = JsonConfig(args.config)
        config_data = config.get_config()
        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        sys.exit(1)
    
    # Get Telegram token from args or env var, add to config_data
    telegram_token = args.token or os.environ.get("TELEGRAM_TOKEN")
    
    # Check for required token
    if telegram_token:
        config_data["telegram_token"] = telegram_token
        logger.info(f"Using Telegram token: {telegram_token[:5]}...{telegram_token[-5:]}")
    elif "telegram_token" not in config_data:
        logger.error("No Telegram token provided. Use --token argument or set TELEGRAM_TOKEN environment variable")
        sys.exit(1)
    
    # Webhook configuration
    webhook_config = None
    if args.webhook:
        if not args.webhook_url:
            # Try to get webhook URL from config
            if "webhook_url" in config_data:
                webhook_url = config_data["webhook_url"]
            else:
                logger.error("Webhook URL not provided. Use --webhook-url or add webhook_url to config")
                sys.exit(1)
        else:
            webhook_url = args.webhook_url
        
        # If the webhook URL doesn't include the token, append it
        if not webhook_url.endswith(config_data["telegram_token"]):
            if webhook_url.endswith('/'):
                webhook_url += config_data["telegram_token"]
            else:
                webhook_url += '/' + config_data["telegram_token"]
        
        webhook_config = {
            "use_webhook": True,
            "webhook_url": webhook_url,
            "webhook_port": args.webhook_port or config_data.get("webhook_port", 8443),
            "cert_path": args.cert_path or config_data.get("cert_path")
        }
        logger.info(f"Using webhook: {webhook_url}")
    
    # Initialize the TelegramInterface
    try:
        # Properly pass the config_file and token to TelegramInterface
        telegram_interface = TelegramInterface(
            config_file=args.config,
            telegram_token=config_data["telegram_token"],
            debug=args.debug
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