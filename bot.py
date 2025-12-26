import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import requests

async def price_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просто пиши тікер - отримуєш ціну Gate Futures"""
    symbol = update.message.text.strip().upper()
    
    try:
        # Gate Futures USDT tickers
        r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=5)
        data = r.json()
        
        for ticker in 
            if ticker["contract"] == f"{symbol}USDT":
                last_price = float(ticker["last"])
                await update.message.reply_text(
                    f"🟠 GATE FUTURES {symbol}USDT\n"
                    f"💰 Ціна: ${last_price:,.6f}\n"
                    f"📊 24h зміна: {ticker['change_percentage']:.2f}%"
                )
                return
        
        await update.message.reply_text(f"❌ {symbol}USDT не знайдено на Gate Futures")
        
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 GATE FUTURES BOT\n\n"
        "Просто пиши тікер:\n"
        "BTC\nSOL\nETH\nPEPE\n\n"
        "/status - статус\n/help - допомога"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 КОМАНДИ:\n\n"
        "BTC - ціна BTCUSDT\n"
        "SOL - ціна SOLUSDT\n"
        "/test - тест\n"
        "/status - статус"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, price_gate))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    print("🚀 Gate Futures Bot запущено!")
    app.run_polling(drop_pending_updates=True)
