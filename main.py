import os
import json
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# تكوين البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7517757393:AAGzb34ezDqZUuUO2mZeMSJfsOAbXr70Oa4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5081207021"))
CONFIG_FILE = "config.json"

# تهيئة ملف التكوين إذا لم يكن موجودًا
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "mode": "auto",  # أو "manual"
            "targets": []
        }, f)

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
        # حفظ الرسالة مؤقتًا للإرسال اليدوي
        context.user_data["pending_message"] = update.message
        keyboard = [[InlineKeyboardButton("📤 إرسال", callback_data="send_pending")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("الرسالة جاهزة للإرسال. اضغط على الزر أدناه للإرسال.", reply_markup=reply_markup)

async def forward_to_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    message = update.message or context.user_data.get("pending_message")
    
    if not message or not config["targets"]:
        return
    
    for target in config["targets"]:
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
            print(f"فشل الإرسال إلى {target}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "send_pending":
        await forward_to_targets(update, context)
        await query.edit_message_text("تم إرسال الرسالة إلى جميع الأهداف.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # تسجيل معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mode", change_mode))
    application.add_handler(CommandHandler("add_target", add_target))
    application.add_handler(CommandHandler("list_targets", list_targets))
    
    # معالجة الرسائل
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # معالجة الضغط على الأزرار
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # بدء البوت
    application.run_polling()

if __name__ == "__main__":
    main()
