import os
import tweepy
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

tracked_users = {}

client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

async def start(update: Update, context):
    await update.message.reply_text(
        "📱 Twitter Monitor\n\n"
        "👤 /track @username - відстежити аккаунт\n"
        "🛑 /stop @username - зупинити\n"
        "/list - список відстежуваних"
    )

async def track_user(update: Update, context):
    if not context.args:
        await update.message.reply_text("Використай: /track @elonmusk")
        return
    
    username = context.args[0].replace("@", "")
    uid = update.effective_user.id
    
    try:
        user = client.get_user(username=username)
        if user.
            tracked_users[uid] = username
            await update.message.reply_text(
                f"✅ Відстежую @{username}\n"
                f"📊 ID: {user.data.id}\n"
                "Нові твіти → Telegram"
            )
        else:
            await update.message.reply_text(f"❌ @{username} не знайдено")
    except:
        await update.message.reply_text("Помилка Twitter API")

async def list_tracked(update: Update, context):
    uid = update.effective_user.id
    if uid in tracked_users:
        await update.message.reply_text(f"📋 Відстежую: @{tracked_users[uid]}")
    else:
        await update.message.reply_text("Нічого не відстежую")

async def check_tweets(update: Update, context):
    uid = update.effective_user.id
    if uid not in tracked_users:
        await update.message.reply_text("Спочатку /track @username")
        return
    
    username = tracked_users[uid]
    try:
        tweets = client.get_users_tweets(id=client.get_user(username=username).data.id, max_results=5)
        
        for tweet in tweets.
            await update.message.reply_text(
                f"🐦 @{username}\n\n"
                f"{tweet.text}\n\n"
                f"🔗 https://twitter.com/{username}/status/{tweet.id}"
            )
    except:
        await update.message.reply_text("Помилка отримання твітів")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track_user))
    app.add_handler(CommandHandler("stop", list_tracked))
    app.add_handler(CommandHandler("list", list_tracked))
    app.add_handler(CommandHandler("check", check_tweets))
    
    print("🚀 Twitter Monitor запущено!")
    app.run_polling(drop_pending_updates=True)
