import functools
from telegram import Update
from telegram.ext import ContextTypes
from config import load_config
from database import get_db_connection

config = load_config()
OWNER_ID = config['owner_id']

def is_owner(user_id):
    return user_id == OWNER_ID

def is_arbitrator(user_id):
    if is_owner(user_id):
        return True
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM arbitrators WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

def restricted(func):
    @functools.wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_arbitrator(user_id):
            await update.message.reply_text("⛔ You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

def owner_only(func):
    @functools.wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_owner(user_id):
            await update.message.reply_text("⛔ This command is restricted to the bot owner.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped
