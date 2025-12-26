import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

def get_gate_price(symbol):
    try:
        r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=5)
        data = r.json()
        
        symbol_usdt = f"{symbol.upper()}USDT"
        
        for ticker in 
            if ticker["contract"] == symbol_usdt:
                price = float(ticker["last"])
                change = float(ticker["change_percentage"])
                return price, change
        
        return None, None
    except:
        return None, None

async def price_handler(update: Update, context):
    symbol = update.message.text.strip().upper()
    price, change = get_gate_price(symbol)
    
    if price:
        await update.message.reply_text(
            f"🟠 GATE {symbol}USDT\n"
            f"${price:,.6f}\n"
            f"{change:+.2f}%"
        )
    else:
        await update.message.reply_text(f"❌ {symbol}USDT")

async def start(update: Update, context):
    await update.message.reply_text(
        "GATE FUTURES\n\n"
        "BTC\nSOL\nETH\nPEPE\nXAN"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, price_handler))
    app.add_handler(CommandHandler("start", start))
    
    print("🚀 GATE BOT")
    app.run_polling(drop_pending_updates=True)
