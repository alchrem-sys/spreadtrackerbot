import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

PRICE1, EXCHANGE1, EXCHANGE2, INTERVAL = range(4)

user_data = {}
user_tasks = {}

EXCHANGE_APIS = {
    "mexc": "https://api.mexc.com/api/v3/ticker/price",
    "binance": "https://api.binance.com/api/v3/ticker/price",
    "gate": "https://api.gateio.ws/api/v4/spot/tickers",
    "bitget": "https://api.bitget.com/api/spot/v1/market/ticker"
}

def get_price(exchange, symbol):
    try:
        if exchange == "gate":
            r = requests.get(f"{EXCHANGE_APIS['gate']}?currency_pair={symbol}USDT", timeout=5)
            return float(r.json()[0]["last"])
        elif exchange == "bitget":
            r = requests.get(f"{EXCHANGE_APIS['bitget']}?symbol={symbol}USDT", timeout=5)
            return float(r.json()["data"][0]["lastPr"])
        else:
            r = requests.get(EXCHANGE_APIS[exchange], params={"symbol": f"{symbol}USDT"}, timeout=5)
            return float(r.json()["price"])
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи: ціна1 ціна2 токени символ\nПриклад: 0.54 0.58 1000 sol")
    return PRICE1

async def get_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("Формат: 0.54 0.58 1000 sol")
        return PRICE1
    
    try:
        price1 = float(parts[0])
        price2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3]
        
        context.user_data.update({
            "price1": price1, "price2": price2, "amount": amount, "symbol": symbol
        })
        
        await update.message.reply_text(
            f"✅ Ціна1: ${price1}\nЦіна2: ${price2}\nТокенів: {amount}\n{symbol}\n\nБіржа1 (mexc/binance/gate/bitget):"
        )
        return EXCHANGE1
    except:
        await update.message.reply_text("Неправильно!")
        return PRICE1

async def get_exchange1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["exchange1"] = update.message.text.strip().lower()
    await update.message.reply_text("Біржа2:")
    return EXCHANGE2

async def get_exchange2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["exchange2"] = update.message.text.strip().lower()
    await update.message.reply_text("Інтервал хвилин (1-60):")
    return INTERVAL

async def get_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text)
        user_id = update.effective_user.id
        data = context.user_data.copy()
        data["interval"] = minutes * 60
        
        user_data[user_id] = data
        
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
        
        app = context.application
        task = asyncio.create_task(monitor(user_id, app))
        user_tasks[user_id] = task
        
        await update.message.reply_text(f"🚀 Запущено! Кожні {minutes} хв\n/status\n/stop")
        return ConversationHandler.END
    except:
        await update.message.reply_text("Число 1-60!")
        return INTERVAL

async def monitor(user_id, app):
    data = user_data[user_id]
    while user_id in user_tasks:
        try:
            p1 = get_price(data["exchange1"], data["symbol"])
            p2 = get_price(data["exchange2"], data["symbol"])
            
            if p1 and p2:
                pnl = data["amount"] * (p2 - p1)
                text = f"{data['symbol'].upper()}\n{data['exchange1']}: ${p1:.6f}\n{data['exchange2']}: ${p2:.6f}\nPnL: ${pnl:+.2f}"
                await app.bot.send_message(user_id, text)
            
            await asyncio.sleep(data["interval"])
        except:
            await asyncio.sleep(60)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        user_data.pop(user_id, None)
        await update.message.reply_text("🛑 Зупинено")
    else:
        await update.message.reply_text("Не запущено")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_
        await update.message.reply_text("Нічого не запущено")
        return
    
    data = user_data[user_id]
    p1 = get_price(data["exchange1"], data["symbol"])
    p2 = get_price(data["exchange2"], data["symbol"])
    
    if p1 and p2:
        pnl = data["amount"] * (p2 - p1)
        await update.message.reply_text(
            f"{data['symbol'].upper()}\n"
            f"{data['exchange1']}: ${p1:.6f}\n"
            f"{data['exchange2']}: ${p2:.6f}\n"
            f"PnL: ${pnl:+.2f}"
        )
    else:
        await update.message.reply_text("Ціни недоступні")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PRICE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prices)],
            EXCHANGE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_exchange1)],
            EXCHANGE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_exchange2)],
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    print("🚀 Бот працює!")
    app.run_polling()

if __name__ == "__main__":
    main()
