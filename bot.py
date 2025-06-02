#!/usr/bin/env python3
# VIBE AI Raider Bot - Main Telegram Bot
# Built with 💖 by VIBE AI - Where quirky meets powerful tech!

# Copyright (c) 2024 VIBE AI Corp.
# Website: www.vibe.airforce
# Telegram: t.me/VIBEaiRforce
# X: x.com/VIBEaiRforce
# Docs: github.com/vibeAIrFORCE/Docs

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, 
    MessageHandler, filters, CallbackQueryHandler
)
from config import TELEGRAM_TOKEN, BOT_NAME, BOT_VERSION
from raid_manager import RaidManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize raid manager
raid_manager = RaidManager()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        f'🚀 Welcome to {BOT_NAME} v{BOT_VERSION}! 🚀\n\n'
        'I help coordinate Twitter engagement campaigns for Web3 projects.\n\n'
        'Use /help to see available commands.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        f"📢 *{BOT_NAME} Commands* 📢\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/raid <tweet_url> <likes> <comments> <reposts> - Start a new raid\n"
        "/cancel - Cancel all active raids in this chat\n"
        "/status - Check active raids status\n\n"
        "Example: /raid https://twitter.com/user/status/123456 100 50 30\n\n"
        "The raid will last for 30 minutes or until all targets are met.\n"
        "Status updates will appear in a single message that updates automatically."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def raid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new raid with the given parameters."""
    args = context.args
    
    if len(args) < 4:
        await update.message.reply_text(
            "⚠️ Incorrect format. Use:\n/raid <tweet_url> <likes> <comments> <reposts>"
        )
        return
    
    tweet_url = args[0]
    
    try:
        targets = {
            'likes': int(args[1]),
            'comments': int(args[2]),
            'retweets': int(args[3])
        }
    except ValueError:
        await update.message.reply_text("⚠️ Targets must be numbers.")
        return
    
    # Validate targets
    if any(value <= 0 for value in targets.values()):
        await update.message.reply_text("⚠️ All targets must be positive numbers.")
        return
    
    # Start raid
    success, result = raid_manager.start_raid(
        context.application,
        update.effective_chat.id,
        tweet_url,
        targets
    )
    
    if success:
        await update.message.reply_text(
            f"🚀 {BOT_NAME} raid started successfully!\n"
            "A status dashboard has been created and will update automatically.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(f"⚠️ {result}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel all active raids in the chat."""
    try:
        success, message = raid_manager.cancel_raid(update.effective_chat.id)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in cancel command: {e}")
        await update.message.reply_text("Error cancelling raids. Please try again.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check status of active raids."""
    chat_id = update.effective_chat.id
    active_count = raid_manager.get_active_raids_count(chat_id)
    
    if active_count > 0:
        raids = raid_manager.get_active_raids(chat_id)
        
        message = f"🚀 *{BOT_NAME} - Active Raids ({active_count})* 🚀\n\n"
        
        for i, raid in enumerate(raids, 1):
            time_left = raid['end_time'] - datetime.now()
            if time_left.total_seconds() <= 0:
                time_str = "0m 0s"
            else:
                minutes, seconds = divmod(time_left.seconds, 60)
                time_str = f"{minutes}m {seconds}s"
                
            message += f"*Raid #{i}*\n"
            message += f"Tweet: [Link]({raid['tweet_url']})\n"
            message += f"Time Left: {time_str}\n"
            message += f"Status: Active\n\n"
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            "No active raids in this chat.\n"
            "Start a new raid with /raid command."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    query = update.callback_query
    
    # Get callback data
    callback_data = query.data
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    
    logger.info(f"Received callback query: {callback_data} from user {user_id} in chat {chat_id}")
    
    # Handle the callback query
    success, message = raid_manager.handle_callback_query(
        query.id, callback_data, chat_id, user_id
    )
    
    # Notify user if needed
    if not success:
        await query.answer(text=message, show_alert=True)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error('Update "%s" caused error "%s"', update, context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred while processing your request. Please try again."
        )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("raid", raid_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Register callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info(f"{BOT_NAME} v{BOT_VERSION} starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()