import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from target_manager import add_target, get_all_targets
import asyncio
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

SEND_AUTOMATICALLY = True
last_forwarded = None

def get_mode_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال تلقائي", callback_data="set_auto")],
        [InlineKeyboardButton("🕹️ إرسال يدوي", callback_data="set_manual")]
    ])

def get_send_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال", callback_data="send_now")]
    ])

async def add_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat
    if user_id == ADMIN_ID:
        if add_target(chat.id):
            await update.message.reply_text("✅ تم إضافة الوجهة بنجاح.")
        else:
            await update.message.reply_text("ℹ️ الوجهة مضافة مسبقًا.")
    else:
        await update.message.reply_text("🚫 ليس لديك صلاحية تنفيذ هذا الأمر.")

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("اختر طريقة الإرسال:", reply_markup=get_mode_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_forwarded, SEND_AUTOMATICALLY

    if update.effective_user.id != ADMIN_ID:
        return

    msg = update.message
    if not msg:
        return

    last_forwarded = msg

    if SEND_AUTOMATICALLY:
        await forward_clean(msg, context)
    else:
        await msg.reply_text("اضغط لإرسال الرسالة إلى الوجهات:", reply_markup=get_send_button())

async def forward_clean(msg, context):
    targets = get_all_targets()
    for target_id in targets:
        try:
            if msg.text:
                await context.bot.send_message(chat_id=target_id, text=msg.text)
            elif msg.photo:
                await context.bot.send_photo(chat_id=target_id, photo=msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video:
                await context.bot.send_video(chat_id=target_id, video=msg.video.file_id, caption=msg.caption)
            elif msg.document:
                await context.bot.send_document(chat_id=target_id, document=msg.document.file_id, caption=msg.caption)
        except Exception as e:
            print(f"❌ Failed to send to {target_id}: {e}")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SEND_AUTOMATICALLY, last_forwarded
    query = update.callback_query
    await query.answer()

    if query.data == "set_auto":
        SEND_AUTOMATICALLY = True
        await query.edit_message_text("✅ تم تفعيل الإرسال التلقائي.")
    elif query.data == "set_manual":
        SEND_AUTOMATICALLY = False
        await query.edit_message_text("🕹️ تم تفعيل الإرسال اليدوي.")
    elif query.data == "send_now":
        if last_forwarded:
            await forward_clean(last_forwarded, context)
            await query.edit_message_text("📤 تم إرسال الرسالة بنجاح.")
        else:
            await query.edit_message_text("⚠️ لا توجد رسالة محفوظة.")

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("addtarget", add_target_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("✅ Bot is running...")
    asyncio.run(app.run_polling())
