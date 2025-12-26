from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import requests
import asyncio
import os

data_store = {}
tasks_store = {}

def get_prices(symbol):
    prices = {}
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol.upper()}USDT", timeout=5)
        prices["Binance"] = float(r.json()["price"])
    except:
        pass
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}USDT", timeout=5)
        prices["MEXC"] = float(r.json()["price"])
    except:
        pass
    return prices

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("test btc")
        return
    symbol = context.args[0].upper()
    prices = get_prices(symbol)
    text = f"{symbol}:\n"
    for ex, p in prices.items():
        text += f"{ex}: ${p:.4f}\n"
    await update.message.reply_text(text)

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    entry1 = float(parts[0])
    entry2 = float(parts[1])
    amount = float(parts[2])
    symbol = parts[3].upper()
    
    uid = update.effective_user.id
    data_store[uid] = {"entry1": entry1, "entry2": entry2, "amount": amount, "symbol": symbol}
    await update.message.reply_text(f"{symbol} налаштовано\nХвилини:")
    return INTERVAL

async def interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mins = int(update.message.text)
    uid = update.effective_user.id
    data = data_store[uid]
    data["interval"] = mins * 60
    
    if uid in tasks_store:
        tasks_store[uid].cancel()
    
    app = context.application
    task = asyncio.create_task(monitor(uid, app))
    tasks_store[uid] = task
    
    await update.message.reply_text(f"{data['symbol']} {mins}хв!")
    return ConversationHandler.END

async def monitor(uid, app):
    data = data_store[uid]
    while uid in tasks_store:
        prices = get_prices(data["symbol"])
        text = f"{data['symbol']}:\n"
        min_p = min(prices.values())
        max_p = max(prices.values())
        pnl = data["amount"] * (max_p - min_p)
        for ex, p in prices.items():
            text += f"{ex}: ${p:.4f}\n"
        text += f"PnL: ${pnl:.2f}"
        await app.bot.send_message(uid, text)
        await asyncio.sleep(data["interval"])

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        await update.message.reply_text("Стоп")
    else:
        await update.message.reply_text("Не запущено")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого немає")
        return
    data = data_store[uid]
    prices = get_prices(data["symbol"])
    text = f"{data['symbol']}:\n"
    for ex, p in prices.items():
        text += f"{ex}: ${p:.4f}\n"
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

conv = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, setup)],
    states={INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv)
app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("status", status))

print("Бот запущено!")
app.run_polling(drop_pending_updates=True)
