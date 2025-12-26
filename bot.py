import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

tracked_accounts = {}
chat_jobs = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Twitter Monitor\n\n"
        "/track @username - відстежити\n"
        "/stop - зупинити\n"
        "/list - список"
    )

async def track_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Використай: /track @elonmusk")
        return
    
    username = context.args[0].lstrip("@")
    chat_id = update.effective_chat.id
    
    tracked_accounts[chat_id] = username
    
    # Симуляція Twitter повідомлення
    await update.message.reply_text(f"✅ Відстежую @{username}")
    
    # Запускаємо фонове сканування кожні 30 сек
    if chat_id in chat_jobs:
        chat_jobs[chat_id].cancel()
    
    job = context.job_queue.run_repeating(
        check_tweets_periodic, 
        interval=30, 
        chat_id=chat_id,
        name=f"track_{username}"
    )
    chat_jobs[chat_id] = job
    
    await update.message.reply_text(f"🔄 Сканую @{username} кожні 30 сек")

async def check_tweets_periodic(context: ContextTypes.DEFAULT_TYPE):
    """Фоновий сканер твітів"""
    chat_id = context.job.chat_id
    username = tracked_accounts.get(chat_id)
    
    if username:
        # Симуляція нового твіту
        import random
        import time
        tweet_id = int(time.time())
        
        tweet_text = f"🐦 НОВИЙ ТВІТ @{username}\n\nTesla to Mars! 🚀\n\n🔗 twitter.com/{username}/status/{tweet_id}"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=tweet_text
        )

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in tracked_accounts:
        await update.message.reply_text(f"📋 @{tracked_accounts[chat_id]}")
    else:
        await update.message.reply_text("Нічого не відстежую")

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id in chat_jobs:
        chat_jobs[chat_id].schedule_removal()
        del chat_jobs[chat_id]
    
    if chat_id in tracked_accounts:
        del tracked_accounts[chat_id]
    
    await update.message.reply_text("🛑 ЗУПИНЕНО")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track_account))
    app.add_handler(CommandHandler("list", list_accounts))
    app.add_handler(CommandHandler("stop", stop_monitor))
    
    print("🚀 Twitter Monitor - МОМЕНТАЛЬНІ ПОВІДОМЛЕННЯ!")
    app.run_polling(drop_pending_updates=True)
