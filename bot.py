import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from target_manager import add_target, get_all_targets

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
AUTO_SEND = False

async def is_admin(update: Update) -> bool:
    """Check if the user is admin"""
    return str(update.effective_user.id) == ADMIN_ID

async def add_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        await update.message.reply_text("❌ ليس لديك صلاحية تنفيذ هذا الأمر.")
        return

    if not context.args:
        await update.message.reply_text("❌ يجب تحديد آي دي الجروب أو القناة.\nاستخدم: /addtarget <chat_id>")
        return

    try:
        target_id = int(context.args[0])
        added = add_target(target_id)
        if added:
            await update.message.reply_text(f"✅ تم إضافة الهدف: `{target_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"ℹ️ الهدف موجود مسبقًا.")
    except ValueError:
        await update.message.reply_text("❌ آي دي غير صالح. يجب أن يكون رقمًا.")

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        await update.message.reply_text("❌ ليس لديك صلاحية تنفيذ هذا الأمر.")
        return

    global AUTO_SEND
    AUTO_SEND = not AUTO_SEND
    status = "تلقائي ✅" if AUTO_SEND else "يدوي ⏳"
    await update.message.reply_text(f"🔁 وضع الإرسال الحالي: {status}")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return

    query = update.callback_query
    await query.answer()

    if query.data == "send_now":
        if "last_message" in context.user_data:
            msg = context.user_data["last_message"]
            success = 0
            failures = 0
            
            for target_id in get_all_targets():
                try:
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=msg.chat_id,
                        message_id=msg.message_id,
                    )
                    success += 1
                except Exception as e:
                    logger.error(f"❌ فشل الإرسال إلى {target_id}: {e}")
                    failures += 1
            
            await query.edit_message_text(
                f"✅ تم الإرسال بنجاح إلى {success} هدف.\n"
                f"❌ فشل الإرسال إلى {failures} هدف."
            )
        else:
            await query.edit_message_text("❌ لا يوجد رسالة محفوظة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return

    if not update.message:
        return

    context.user_data["last_message"] = update.message

    if AUTO_SEND:
        success = 0
        failures = 0
        
        for target_id in get_all_targets():
            try:
                await context.bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id,
                )
                success += 1
            except Exception as e:
                logger.error(f"❌ فشل الإرسال إلى {target_id}: {e}")
                failures += 1
        
        await update.message.reply_text(
            f"📤 تم الإرسال التلقائي إلى {success} هدف.\n"
            f"❌ فشل الإرسال إلى {failures} هدف."
        )
    else:
        keyboard = [[InlineKeyboardButton("📤 إرسال", callback_data="send_now")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📝 هل تريد إرسال هذه الرسالة؟",
            reply_markup=reply_markup
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"حدث خطأ: {context.error}")
    if update and hasattr(update, 'message'):
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة طلبك.")

def main():
    """Run the bot."""
    if not BOT_TOKEN or not ADMIN_ID:
        raise ValueError("BOT_TOKEN and ADMIN_ID must be set in environment variables")

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("addtarget", add_target_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("🤖 Bot is starting...")
    application.run_polling()
