import os
import json
from keep_alive import keep_alive
from dotenv import load_dotenv
from telegram import Bot, Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from flask import Flask
from threading import Thread
import requests
import time

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))  # Default to 0 if not set
DATA_FILE = 'data.json'

# Initialize data structure
def init_data():
    return {
        'targets': [],
        'mode': 'auto'  # or 'manual'
    }

# Load data from JSON file
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = init_data()
        save_data(data)
        return data

# Save data to JSON file
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Check if user is admin
def is_admin(update: Update):
    return update.effective_user.id == ADMIN_ID

async def send_to_targets(application, message=None, chat_id=None, media_group=None):
    data = load_data()
    bot = application.bot
    
    for target in data['targets']:
        try:
            if media_group:
                media = []
                for idx, media_item in enumerate(media_group):
                    if media_item.photo:
                        if idx == 0:
                            media.append(InputMediaPhoto(media_item.photo[-1].file_id, caption=message))
                        else:
                            media.append(InputMediaPhoto(media_item.photo[-1].file_id))
                    elif media_item.video:
                        if idx == 0:
                            media.append(InputMediaVideo(media_item.video.file_id, caption=message))
                        else:
                            media.append(InputMediaVideo(media_item.video.file_id))
                    elif media_item.document:
                        if idx == 0:
                            media.append(InputMediaDocument(media_item.document.file_id, caption=message))
                        else:
                            media.append(InputMediaDocument(media_item.document.file_id))
                
                await bot.send_media_group(chat_id=target, media=media)
            elif message:
                await bot.send_message(chat_id=target, text=message)
            elif chat_id:
                await bot.copy_message(chat_id=target, from_chat_id=chat_id, message_id=message.message_id)
        except Exception as e:
            print(f"Error sending to {target}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    
    await update.message.reply_text(
        "مرحباً بك في بوت التوجيه!\n"
        "استخدم /mode لتغيير وضع الإرسال (تلقائي/يدوي)\n"
        "استخدم /addtarget لإضافة قناة أو مجموعة\n"
        "استخدم /targets لعرض قائمة الأهداف"
    )

async def change_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    
    data = load_data()
    keyboard = [
        [
            InlineKeyboardButton("تلقائي", callback_data='mode_auto'),
            InlineKeyboardButton("يدوي", callback_data='mode_manual'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"وضع الإرسال الحالي: {data['mode']}\nاختر الوضع الجديد:",
        reply_markup=reply_markup
    )

async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء إدخال معرف القناة أو المجموعة بعد الأمر /addtarget")
        return
    
    target = context.args[0]
    data = load_data()
    
    if target not in data['targets']:
        data['targets'].append(target)
        save_data(data)
        await update.message.reply_text(f"تمت إضافة {target} إلى قائمة الأهداف")
    else:
        await update.message.reply_text(f"{target} موجود بالفعل في قائمة الأهداف")

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    
    data = load_data()
    if not data['targets']:
        await update.message.reply_text("لا توجد أهداف محددة بعد")
    else:
        targets_list = "\n".join(data['targets'])
        await update.message.reply_text(f"قائمة الأهداف:\n{targets_list}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update):
        return
    
    data = load_data()
    
    if query.data.startswith('mode_'):
        new_mode = query.data.split('_')[1]
        data['mode'] = new_mode
        save_data(data)
        await query.edit_message_text(f"تم تغيير وضع الإرسال إلى: {new_mode}")
    
    elif query.data == 'send_message':
        message_data = context.user_data.get('pending_message')
        if message_data:
            await send_to_targets(context.application, **message_data)
            await query.edit_message_text("تم إرسال الرسالة إلى جميع الأهداف")
            del context.user_data['pending_message']

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    
    data = load_data()
    message = update.message
    
    if data['mode'] == 'auto':
        if message.media_group_id:
            media_group = await message.get_media_group()
            await send_to_targets(context.application, message.caption, media_group=media_group)
        elif message.text:
            await send_to_targets(context.application, message.text)
        else:
            await send_to_targets(context.application, None, chat_id=message.chat_id, message=message)
    else:
        keyboard = [[InlineKeyboardButton("📤 إرسال", callback_data='send_message')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data['pending_message'] = {
            'chat_id': message.chat_id,
            'message': message
        }
        
        if message.media_group_id:
            media_group = await message.get_media_group()
            context.user_data['pending_message']['media_group'] = media_group
            context.user_data['pending_message']['message'] = message.caption
            
            first_media = media_group[0]
            if first_media.photo:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=first_media.photo[-1].file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )
            elif first_media.video:
                await context.bot.send_video(
                    chat_id=ADMIN_ID,
                    video=first_media.video.file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )
            elif first_media.document:
                await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=first_media.document.file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )
        elif message.text:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{message.text}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                reply_markup=reply_markup
            )
        else:
            if message.photo:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=message.photo[-1].file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=ADMIN_ID,
                    video=message.video.file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=message.document.file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=ADMIN_ID,
                    audio=message.audio.file_id,
                    caption=f"{message.caption}\n\nالرسالة جاهزة للإرسال إلى {len(data['targets'])} هدف",
                    reply_markup=reply_markup
                )

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def ping():
    while True:
        requests.get("https://telegram-forward-wa4p.onrender.com")
        time.sleep(300)  # Ping كل 5 دقائق

Thread(target=ping).start()

def main():
    # Initialize data file if not exists
    load_data()
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mode", change_mode))
    application.add_handler(CommandHandler("addtarget", add_target))
    application.add_handler(CommandHandler("targets", list_targets))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
    main()
