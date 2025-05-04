#!/usr/bin/env python3
"""
Test script for Telegram command handlers
"""
import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger("test_handler")

# Handler functions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    logger.info(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text("Hello! I'm a test bot. I'm working correctly!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    logger.info(f"Received /help command from user {update.effective_user.id}")
    await update.message.reply_text("This is a test bot to check if command handlers are working.")

async def main() -> None:
    """Start the bot."""
    # Get the token from command line
    if len(sys.argv) < 2:
        print("Usage: python test_handler.py <telegram_token>")
        return
    
    token = sys.argv[1]
    logger.info(f"Starting bot with token: {token[:5]}...{token[-5:]}")
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Starting bot in polling mode")
    await application.initialize()
    await application.updater.start_polling()
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    # Keep the bot running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        logger.info("Stopping bot")
        await application.updater.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 