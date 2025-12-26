import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

PRICE1, EXCHANGE1, EXCHANGE2, INTERVAL = range(4)

data_store = {}
tasks_store = {}

def get_price(exchange, symbol):
    try:
        if exchange == "mexc":
            r = requests.get("https://api.mexc.com/api/v3/ticker/price", params={"symbol": f"{symbol}USDT"})
            return float(r.json()["price"])
        elif exchange == "binance":
            r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": f"{symbol}USDT"})
            return float(r.json()["price"])
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ціна1 ціна2 токени символ\nПриклад: 0.54 0.58 1000 sol")
    return PRICE1

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4: 
        await update.message.reply_text("0.54 0.58 1000 sol")
        return PRICE1
    
    price1 = float(parts[0])
    price2 = float(parts[1])
    amount = float(parts[2])
    symbol = parts[3]
    
    context.user_data = {
        "p1": price1, "p2": price2, "amt": amount, "sym": symbol
    }
    
    await update.message.reply_text("Біржа1 (mexc/binance):")
    return EXCHANGE1

async def exch1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ex1"] = update.message.text.strip().lower()
    await update.message.reply_text("Біржа2:")
    return EXCHANGE2

async def exch2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ex2"] = update.message.text.strip().lower()
    await update.message.reply_text("Хвилини (1-60):")
    return INTERVAL

async def interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mins = int(update.message.text)
    uid = update.effective_user.id
    data = context.user_data.copy()
    data["sec"] = mins * 60
    
    data_store[uid] = data
    
    if uid in tasks_store:
        tasks_store[uid].cancel()
    
    app = context.application
    task = asyncio.create_task(run_monitor(uid, app))
    tasks_store[uid] = task
    
    await update.message.reply_text(f"Запущено! {mins} хв\n/status /stop")
    return ConversationHandler.END

async def run_monitor(uid, app):
    data = data_store[uid]
    while uid in tasks_store:
        p1 = get_price(data["ex1"], data["sym"])
        p2 = get_price(data["ex2"], data["sym"])
        
        if p1 and p2:
            pnl = data["amt"] * (p2 - p1)
            text = f"{data['sym'].upper()}\n{data['ex1']}: ${p1:.6f}\n{data['ex2']}: ${p2:.6f}\nPnL: ${pnl:+.2f}"
            await app.bot.send_message(uid, text)
        
        await asyncio.sleep(data["sec"])

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("Зупинено")
    else:
        await update.message.reply_text("Не запущено")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого немає")
        return
    
    data = data_store[uid]
    p1 = get_price(data["ex1"], data["sym"])
    p2 = get_price(data["ex2"], data["sym"])
    
    if p1 and p2:
        pnl = data["amt"] * (p2 - p1)
        await update.message.reply_text(
            f"{data['sym'].upper()}\n"
            f"{data['ex1']}: ${p1:.6f}\n"
            f"{data['ex2']}: ${p2:.6f}\n"
            f"PnL: ${pnl:+.2f}"
        )
    else:
        await update.message.reply_text("Ціни немає")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PRICE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, prices)],
            EXCHANGE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, exch1)],
            EXCHANGE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, exch2)],
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    print("Бот запущено!")
    app.run_polling()
