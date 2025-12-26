import os
import asyncio
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, filters

tracked_accounts = {}
last_message_time = {}

async def start(update: Update, context):
    await update.message.reply_text(
        "🚀 Twitter Monitor 1s\n\n"
        "/track @username\n"
        "/stop\n"
        "/status"
    )

async def track_account(update: Update, context):
    username = context.args[0].lstrip("@") if context.args else "elonmusk"
    chat_id = update.effective_chat.id
    
    tracked_accounts[chat_id] = username
    last_message_time[chat_id] = 0
    
    await update.message.reply_text(f"✅ @{username} - кожну секунду!")

async def status(update: Update, context):
    chat_id = update.effective_chat.id
    if chat_id in tracked_accounts:
        await update.message.reply_text(f"📊 @{tracked_accounts[chat_id]} - активний")
    else:
        await update.message.reply_text("Нічого не відстежую")

async def stop_monitor(update: Update, context):
    chat_id = update.effective_chat.id
    tracked_accounts.pop(chat_id, None)
    last_message_time.pop(chat_id, None)
    await update.message.reply_text("🛑 ЗУПИНЕНО")

async def main_loop(app):
    """Оновлення КОЖНУ СЕКУНДУ"""
    while True:
        current_time = time.time()
        
        for chat_id, username in list(tracked_accounts.items()):
            if chat_id not in last_message_time or current_time - last_message_time[chat_id] >= 1:
                tweet_id = int(current_time * 1000)
                message = f"🐦 @{username}\n📱 {current_time:.0f}s\n🔗 twitter.com/{username}/status/{tweet_id}"
                
                try:
                    await app.bot.send_message(chat_id=chat_id, text=message)
                    last_message_time[chat_id] = current_time
                except:
                    pass
        
        await asyncio.sleep(1)  # 1 секунда

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track_account))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop_monitor))
    
    print("🚀 1s UPDATE BOT!")
    
    # Запускаємо основну петлю
    loop = asyncio.get_event_loop()
    loop.create_task(main_loop(app))
    
    app.run_polling(drop_pending_updates=True)
