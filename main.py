#!/usr/bin/env python3
import logging
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters
)
from keep_alive import keep_alive
keep_alive()


# Configuration - EDIT THESE VALUES
BOT_TOKEN = "7517757393:AAE4TxX-OeR7S9AjBPqCwvAa8cArVs4CbWE"  # From @BotFather
GROUP_ID = -1002320071203  # Your group/channel ID (must include -100 for channels)

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and resend them to the specified group."""
    try:
        message = update.effective_message
        if not message:
            return

        # Check if message is forwarded
        is_forwarded = any([
            message.forward_from,
            message.forward_from_chat,
            message.forward_sender_name,
            message.forward_date
        ])

        if not is_forwarded:
            return

        # Copy the message to the target group
        await message.copy(
            chat_id=GROUP_ID,
            caption=message.caption,
            caption_entities=message.caption_entities
        )

    except Exception as e:
        logger.error(f"Error handling message: {e}")

def main() -> None:
    """Start the bot."""
    # Create the Application with default settings
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handler for all message types except commands
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        handle_message
    ))

    logger.info("Bot is running. Forward messages to it!")
    application.run_polling()

if __name__ == "__main__":
    main()
