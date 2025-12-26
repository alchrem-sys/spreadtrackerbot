from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import os

async def start(update, context):
    await update.message.reply_text("🚀 Twitter Monitor\n/track @username")

async def track(update, context):
    username = context.args[0].replace("@", "") if context.args else "elonmusk"
    await update.message.reply_text(f"✅ Відстежую @{username}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track))
    print("Bot OK!")
    app.run_polling(drop_pending_updates=True)
