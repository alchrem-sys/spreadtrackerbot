import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

tracked_accounts = {}

async def start(update: Update, context):
    await update.message.reply_text(
        "🚀 Twitter Monitor\n\n"
        "/track @username - додати\n"
        "/list - список\n"
        "/check - перевірити ОДИН РАЗ"
    )

async def track_account(update: Update, context):
    if not context.args:
        await update.message.reply_text("Використай: /track @elonmusk")
        return
    
    username = context.args[0].lstrip("@")
    chat_id = update.effective_chat.id
    
    tracked_accounts[chat_id] = username
    await update.message.reply_text(f"✅ Додано @{username} до списку")

async def list_accounts(update: Update, context):
    chat_id = update.effective_chat.id
    if chat_id in tracked_accounts:
        await update.message.reply_text(f"📋 @{tracked_accounts[chat_id]}")
    else:
        await update.message.reply_text("Список порожній")

async def check_once(update: Update, context):
    """ОДИН РАЗ перевіряє твіти"""
    chat_id = update.effective_chat.id
    if chat_id not in tracked_accounts:
        await update.message.reply_text("Спочатку /track @username")
        return
    
    username = tracked_accounts[chat_id]
    
    await update.message.reply_text(
        f"🔍 Шукаю нові твіти @{username}...\n"
        f"(Симуляція - натисни /check ще раз)"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track_account))
    app.add_handler(CommandHandler("list", list_accounts))
    app.add_handler(CommandHandler("check", check_once))
    
    print("🚀 Twitter Monitor - БЕЗ СПАМУ!")
    app.run_polling(drop_pending_updates=True)
