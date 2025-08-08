import os
import json
import asyncio
import logging
from aiohttp import web
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7517757393:AAGzb34ezDqZUuUO2mZeMSJfsOAbXr70Oa4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5081207021"))
CONFIG_FILE = "config.json"
PORT = int(os.getenv("PORT", 8080))

class KeepAlive:
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/", self.health_check)
        self.runner = None
        self.site = None

    async def health_check(self, request):
        return web.Response(text="Bot is alive!")

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        logger.info(f"Keep-alive server running on port {self.port}")

    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

# Initialize config
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"mode": "auto", "targets": []}, f)

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# Bot command handlers
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
            await context.bot.send_message(ADMIN_ID, f"فشل الإرسال إلى {target}: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "send_to_all":
        await forward_to_targets(update, context)
        await query.edit_message_text("تم إرسال الرسالة إلى جميع الأهداف.")
    elif query.data.startswith("send_to_"):
        target = query.data[8:]
        await forward_to_targets(update, context, selected_targets=[target])
        await query.edit_message_text(f"تم إرسال الرسالة إلى {target}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    logger.error(msg="Exception while handling an update:", exc_info=error)
    
    if isinstance(error, Conflict):
        logger.warning("Conflict detected - another instance may be running")
        # Don't exit, just wait and try again
        await asyncio.sleep(5)
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"حدث خطأ: {str(error)}"
        )

async def main():
    # Initialize keep-alive server
    keep_alive = KeepAlive(port=PORT)
    await keep_alive.start()
    
    try:
        # Create application
        application = Application.builder().token(TOKEN).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("mode", change_mode))
        application.add_handler(CommandHandler("add_target", add_target))
        application.add_handler(CommandHandler("remove_target", remove_target))
        application.add_handler(CommandHandler("list_targets", list_targets))
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_error_handler(error_handler)
        
        # Start polling with error recovery
        while True:
            try:
                logger.info("Starting bot...")
                await application.initialize()
                await application.start()
                await application.updater.start_polling()
                
                # Keep the bot running
                while True:
                    await asyncio.sleep(3600)
                    
            except Conflict as e:
                logger.warning(f"Conflict error: {e}. Restarting in 5 seconds...")
                await asyncio.sleep(5)
                continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}. Restarting in 10 seconds...")
                await asyncio.sleep(10)
                continue
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("Shutting down...")
        await keep_alive.stop()
        if 'application' in locals():
            await application.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
