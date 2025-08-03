import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from target_manager import add_target, get_all_targets

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# الإعدادات
ADMIN_ONLY = True  # البوت يعمل فقط لأوامر الأدمن
AUTO_SEND = False  # الوضع الافتراضي: لا يتم الإرسال التلقائي إلا بعد ضغط زر

# إعدادات السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# إضافة هدف جديد
async def add_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ يجب تحديد آي دي الجروب أو القناة.")
        return

    try:
        target_id = int(context.args[0])
        added = add_target(target_id)
        if added:
            await update.message.reply_text(f"✅ تم إضافة الهدف: `{target_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"ℹ️ الهدف موجود مسبقًا.")
    except ValueError:
        await update.message.reply_text("❌ آي دي غير صالح.")


# تغيير وضع الإرسال التلقائي / اليدوي
async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return

    global AUTO_SEND
    AUTO_SEND = not AUTO_SEND
    status = "تلقائي ✅" if AUTO_SEND else "يدوي ⏳"
    await update.message.reply_text(f"🔁 وضع الإرسال الحالي: {status}")


# زر الإرسال اليدوي
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return

    query = update.callback_query
    await query.answer()

    if query.data == "send_now":
        if "last_message" in context.user_data:
            msg = context.user_data["last_message"]
            for target_id in get_all_targets():
                try:
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=msg.chat_id,
                        message_id=msg.message_id,
                    )
                except Exception as e:
                    logger.error(f"❌ فشل الإرسال إلى {target_id}: {e}")
            await query.edit_message_text("✅ تم الإرسال بنجاح.")
        else:
            await query.edit_message_text("❌ لا يوجد رسالة محفوظة.")


# التعامل مع كل الرسائل
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return

    context.user_data["last_message"] = update.message

    if AUTO_SEND:
        for target_id in get_all_targets():
            try:
                await context.bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id,
                )
            except Exception as e:
                logger.error(f"❌ فشل الإرسال إلى {target_id}: {e}")
    else:
        keyboard = [[InlineKeyboardButton("📤 إرسال", callback_data="send_now")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📝 هل تريد إرسال هذه الرسالة؟", reply_markup=reply_markup)


# تشغيل البوت
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("addtarget", add_target_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("🤖 Bot is running...")
    await app.run_polling()
