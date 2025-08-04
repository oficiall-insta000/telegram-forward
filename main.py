import os
import json
import logging
from threading import Thread
from flask import Flask
import requests
from telegram import (
    Bot, Update,
    InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# ======================
# CONFIGURATION
# ======================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
DATA_FILE = 'data.json'
RENDER_URL = "https://your-render-service.onrender.com"  # Replace with your actual URL

# ======================
# FLASK KEEP-ALIVE
# ======================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is alive and running!"

def ping_server():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
            logging.info("Keep-alive ping successful")
        except Exception as e:
            logging.error(f"Ping failed: {e}")
        time.sleep(300)  # Ping every 5 minutes

# ======================
# BOT CORE FUNCTIONS
# ======================
def init_data():
    return {'targets': [], 'mode': 'auto'}

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = init_data()
        save_data(data)
        return data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_admin(update: Update):
    return update.effective_user.id == ADMIN_ID

async def send_to_targets(context: ContextTypes.DEFAULT_TYPE, **kwargs):
    data = load_data()
    for target in data['targets']:
        try:
            if 'media_group' in kwargs:
                media = []
                for idx, item in enumerate(kwargs['media_group']):
                    media.append(
                        InputMediaPhoto(item.photo[-1].file_id, 
                        caption=kwargs.get('caption') if idx == 0 else None
                    ) if item.photo else (
                        InputMediaVideo(item.video.file_id,
                        caption=kwargs.get('caption') if idx == 0 else None
                    ) if item.video else (
                        InputMediaDocument(item.document.file_id,
                        caption=kwargs.get('caption') if idx == 0 else None
                    )
                await context.bot.send_media_group(target, media=media)
            elif 'message_obj' in kwargs:
                await context.bot.copy_message(
                    chat_id=target,
                    from_chat_id=kwargs['chat_id'],
                    message_id=kwargs['message_obj'].message_id
                )
            else:
                await context.bot.send_message(target, text=kwargs['text'])
        except Exception as e:
            logging.error(f"Failed to send to {target}: {e}")

# ======================
# COMMAND HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    
    data = load_data()
    await update.message.reply_text(
        f"⚙️ Bot Status:\n"
        f"- Mode: {'AUTO' if data['mode'] == 'auto' else 'MANUAL'}\n"
        f"- Targets: {len(data['targets'])}\n"
        f"- Uptime Monitor: {RENDER_URL}\n\n"
        "📋 Commands:\n"
        "/mode - Switch mode\n"
        "/addtarget @channel - Add target\n"
        "/targets - List targets"
    )

async def change_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    
    await update.message.reply_text(
        "Select mode:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("AUTO", callback_data='mode_auto'),
            InlineKeyboardButton("MANUAL", callback_data='mode_manual')
        ]])
    )

async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    
    if not context.args:
        await update.message.reply_text("Usage: /addtarget @channel")
        return
    
    target = context.args[0].lstrip('@')
    data = load_data()
    
    if target not in data['targets']:
        data['targets'].append(target)
        save_data(data)
        await update.message.reply_text(f"✅ Added {target}")
    else:
        await update.message.reply_text(f"⚠️ {target} already exists")

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    
    data = load_data()
    await update.message.reply_text(
        "📌 Targets:\n" + "\n".join(f"• {t}" for t in data['targets']) if data['targets'] else "No targets yet"
    )

# ======================
# MESSAGE HANDLING
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    
    data = load_data()
    msg = update.message
    
    try:
        if data['mode'] == 'auto':
            if msg.media_group_id:
                await send_to_targets(
                    context,
                    media_group=await msg.get_media_group(),
                    caption=msg.caption
                )
            else:
                await send_to_targets(
                    context,
                    chat_id=msg.chat_id,
                    message_obj=msg,
                    text=msg.text or msg.caption
                )
        else:
            context.user_data['pending'] = {
                'chat_id': msg.chat_id,
                'message': msg
            }
            
            if msg.media_group_id:
                context.user_data['pending']['media_group'] = await msg.get_media_group()
                preview = context.user_data['pending']['media_group'][0]
                caption = f"📦 Media Group\n{msg.caption or ''}\n\nSend to {len(data['targets'])} targets?"
            else:
                preview = msg
                caption = f"{msg.text or msg.caption or 'Media'}\n\nSend to {len(data['targets'])} targets?"
            
            if msg.photo:
                await context.bot.send_photo(
                    ADMIN_ID, preview.photo[-1].file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📤 SEND", callback_data='confirm_send')
                    ]])
                )
            elif msg.text:
                await context.bot.send_message(
                    ADMIN_ID, caption,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📤 SEND", callback_data='confirm_send')
                    ]])
                )
    except Exception as e:
        logging.error(f"Handle message error: {e}")

# ======================
# BUTTON HANDLERS
# ======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update): return
    
    if query.data.startswith('mode_'):
        data = load_data()
        data['mode'] = query.data.split('_')[1]
        save_data(data)
        await query.edit_message_text(f"Mode set to {data['mode'].upper()}")
    elif query.data == 'confirm_send':
        pending = context.user_data.get('pending')
        if pending:
            try:
                await send_to_targets(context, **pending)
                await query.edit_message_text("✅ Sent successfully")
            except Exception as e:
                await query.edit_message_text(f"❌ Failed: {e}")
            finally:
                context.user_data.pop('pending', None)

# ======================
# APPLICATION SETUP
# ======================
def run_flask():
    app.run(host='0.0.0.0', port=8080)

def main():
    # Start keep-alive
    Thread(target=ping_server).start()
    Thread(target=run_flask).start()
    
    # Configure bot
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    handlers = [
        CommandHandler('start', start),
        CommandHandler('mode', change_mode),
        CommandHandler('addtarget', add_target),
        CommandHandler('targets', list_targets),
        CallbackQueryHandler(button_handler),
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    ]
    
    for handler in handlers:
        application.add_handler(handler)
    
    # Start bot
    application.run_polling()

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main()
