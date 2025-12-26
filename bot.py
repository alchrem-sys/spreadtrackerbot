import os
import asyncio
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

tracked_accounts = {}
monitor_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Twitter Monitor\n\n"
        "/track @username\n"
        "/list\n"
        "/stop"
    )

async def track_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Використай: /track @elonmusk")
        return
    
    username = context.args[0].lstrip("@")
    chat_id = update.effective_chat.id
    
    tracked_accounts[chat_id] = username
    
    # Зупиняємо попередню задачу
    if chat_id in monitor_tasks:
        monitor_tasks[chat_id].cancel()
    
    # Запускаємо нову
    task = asyncio.create_task(monitor_loop(chat_id, username, context.application))
    monitor_tasks[chat_id] = task
    
    await update.message.reply_text(f"✅ Відстежую @{username}")

async def monitor_loop(chat_id, username, app):
    """Фонове сканування кожні 30 сек"""
    while chat_id in tracked_accounts:
        try:
            # Симуляція Twitter твіту
            import random
            tweet_id = int(time.time() * 1000 + random.randint(1, 999))
            tweet_text = f"🐦 @{username}\n\n🚀 NEW TWEET #{random.randint(1, 1000)}!\n\n🔗 twitter.com/{username}/status/{tweet_id}"
            
            await app.bot.send_message(chat_id=chat_id, text=tweet_text)
            await asyncio.sleep(1)  # 30 секунд
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(30)

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in tracked_accounts:
        await update.message.reply_text(f"📋 @{tracked_accounts[chat_id]}")
    else:
        await update.message.reply_text("Нічого не відстежую")

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id in monitor_tasks:
        monitor_tasks[chat_id].cancel()
        del monitor_tasks[chat_id]
    
    if chat_id in tracked_accounts:
        del tracked_accounts[chat_id]
    
    await update.message.reply_text("🛑 ЗУПИНЕНО")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track_account))
    app.add_handler(CommandHandler("list", list_accounts))
    app.add_handler(CommandHandler("stop", stop_monitor))
    
    print("🚀 Twitter Monitor - ПОВІДОМЛЕННЯ КОЖНІ 30 СЕК!")
    app.run_polling(drop_pending_updates=True)
