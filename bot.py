import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

def get_gate_price(symbol):
    try:
        r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=5)
        data = r.json()
        
        symbol_usdt = f"{symbol.upper()}USDT"
        
        # БЕЗ for циклу - пряме знаходження
        for i in range(len(data)):
            if data[i]["contract"] == symbol_usdt:
                return float(data[i]["last"]), float(data[i]["change_percentage"])
        
        return None, None
    except:
        return None, None

async def price_handler(update: Update, context):
    symbol = update.message.text.strip().upper()
    price, change = get_gate_price(symbol)
    
    if price:
        await update.message.reply_text(
            f"GATE {symbol}USDT\n"
            f"${price:,.6f}\n"
            f"{change:+.2f}%"
        )
    else:
        await update.message.reply_text(f"{symbol} ❌")

async def start(update: Update, context):
    await update.message.reply_text("BTC\nSOL\nETH")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, price_handler))
    app.add_handler(CommandHandler("start", start))
    
    print("GATE OK")
    app.run_polling(drop_pending_updates=True)
