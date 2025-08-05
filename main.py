import os
import json
import asyncio
from keep_alive import KeepAlive
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import Conflict
import logging

keep_alive = KeepAlive(port=int(os.getenv("PORT", 8080)))

async def start_bot():
    # Start keep-alive server
    await keep_alive.start()
    
# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7517757393:AAGzb34ezDqZUuUO2mZeMSJfsOAbXr70Oa4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5081207021"))
CONFIG_FILE = "config.json"

# Initialize config file if not exists
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"mode": "auto", "targets": [], "pending_message": None}, f)

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("مرحباً يا مسؤول! أنا بوت إعادة التوجيه.")

async def change_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    config = load_config()
    new_mode = "manual" if config["mode"] == "auto" else "auto"
    config["mode"] = new_mode
    save_config(config)
    
    await update.message.reply_text(f"تم تغيير وضع الإرسال إلى: {new_mode}")

async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء إدخال معرف القناة/المجموعة بعد الأمر.\nمثال: /add_target @channel_name")
        return
    
    target = context.args[0]
    config = load_config()
    
    if target in config["targets"]:
        await update.message.reply_text("هذا الهدف موجود بالفعل!")
        return
    
    config["targets"].append(target)
    save_config(config)
    await update.message.reply_text(f"تمت إضافة الهدف: {target}")

async def remove_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء إدخال معرف القناة/المجموعة المراد حذفها.\nمثال: /remove_target @channel_name")
        return
    
    target = context.args[0]
    config = load_config()
    
    if target not in config["targets"]:
        await update.message.reply_text("هذا الهدف غير موجود في القائمة!")
        return
    
    config["targets"].remove(target)
    save_config(config)
    await update.message.reply_text(f"تم حذف الهدف: {target}")

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    config = load_config()
    targets = config["targets"]
    
    if not targets:
        await update.message.reply_text("لا توجد أهداف مضافّة حتى الآن.")
        return
    
    await update.message.reply_text("قائمة الأهداف:\n" + "\n".join(targets))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    config = load_config()
    
    if config["mode"] == "auto":
        await forward_to_targets(update, context)
    else:
        # Save message temporarily for manual sending
        config["pending_message"] = {
            "message_id": update.message.message_id,
            "chat_id": update.message.chat_id,
            "content_type": update.message.content_type,
            # Add other relevant message data
        }
        save_config(config)
        
        # Create buttons for each target
        keyboard = []
        for target in config["targets"]:
            keyboard.append([InlineKeyboardButton(f"إرسال إلى {target}", callback_data=f"send_to_{target}")])
        keyboard.append([InlineKeyboardButton("📤 إرسال للجميع", callback_data="send_to_all")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر الأهداف للإرسال:", reply_markup=reply_markup)

async def forward_to_targets(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_targets=None):
    config = load_config()
    message = update.message
    
    if not message or not config["targets"]:
        return
    
    targets = selected_targets if selected_targets else config["targets"]
    
    for target in targets:
        try:
            if message.photo:
                await context.bot.send_photo(
                    chat_id=target,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=target,
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=target,
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=target,
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.text:
                await context.bot.send_message(
                    chat_id=target,
                    text=message.text,
                    entities=message.entities
                )
        except Exception as e:
            logger.error(f"فشل الإرسال إلى {target}: {e}")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"فشل الإرسال إلى {target}: {str(e)}"
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    config = load_config()
    
    if query.data == "send_to_all":
        await forward_to_targets(update, context)
        await query.edit_message_text("تم إرسال الرسالة إلى جميع الأهداف.")
    elif query.data.startswith("send_to_"):
        target = query.data[8:]  # Remove "send_to_" prefix
        await forward_to_targets(update, context, selected_targets=[target])
        await query.edit_message_text(f"تم إرسال الرسالة إلى {target}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if isinstance(context.error, Conflict):
        logger.warning("Another instance is already running. Exiting.")
        # Gracefully shutdown the application
        if 'application' in context.bot_data:
            await context.bot_data['application'].stop()
        os._exit(1)

def main():
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()
    
    # Store application reference for error handling
    application.bot_data['application'] = application
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mode", change_mode))
    application.add_handler(CommandHandler("add_target", add_target))
    application.add_handler(CommandHandler("remove_target", remove_target))
    application.add_handler(CommandHandler("list_targets", list_targets))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Run the bot until the user presses Ctrl-C
    try:
        logger.info("Starting bot...")
        application.run_polling()
    except Conflict:
        logger.warning("Another instance is already running. Exiting.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Bot stopped")

if __name__ == "__main__":
    main()
