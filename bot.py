import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

tracked_users = {}

async def start(update: Update, context):
    await update.message.reply_text(
        "📱 Twitter Monitor\n\n"
        "/track @username\n"
        "/list\n"
        "/check"
    )

async def track_user(update: Update, context):
    if not context.args:
        await update.message.reply_text("/track @elonmusk")
        return
    
    username = context.args[0].replace("@", "")
    uid = update.effective_user.id
    tracked_users[uid] = username
    
    await update.message.reply_text(f"✅ Відстежую @{username}")

async def list_tracked(update: Update, context):
    uid = update.effective_user.id
    if uid in tracked_users:
        await update.message.reply_text(f"📋 @{tracked_users[uid]}")
    else:
        await update.message.reply_text("Нічого")

async def check_tweets(update: Update, context):
    uid = update.effective_user.id
    if uid in tracked_users:
        username = tracked_users[uid]
        await update.message.reply_text(f"🧪 Перевіряю @{username}...")
    else:
        await update.message.reply_text("Спочатку /track")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track_user))
    app.add_handler(CommandHandler("list", list_tracked))
    app.add_handler(CommandHandler("check", check_tweets))
    
    print("🚀 Twitter Monitor OK!")
    app.run_polling(drop_pending_updates=True)
