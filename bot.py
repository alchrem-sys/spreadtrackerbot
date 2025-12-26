import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_prices(symbol):
    prices = {}
    symbol_usdt = f"{symbol.upper()}USDT"
    
    r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
    try:
        prices["BINANCE"] = float(r.json()["price"])
    except:
        pass
    
    r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol_usdt}", timeout=3)
    try:
        prices["MEXC"] = float(r.json()["price"])
    except:
        pass
    
    return prices

async def start_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    
    try:
        entry1 = float(parts[0])
        entry2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        prices = get_prices(symbol)
        
        text = f"{symbol}\n\n"
        text += f"Вхід: ${entry1} → ${entry2}\n"
        text += f"{amount} шт\n\n"
        
        min_p = 999999
        max_p = 0
        min_ex = ""
        max_ex = ""
        
        for ex, p in prices.items():
            text += f"{ex}: ${p}\n"
            if p < min_p:
                min_p = p
                min_ex = ex
            if p > max_p:
                max_p = p
                max_ex = ex
        
        spread = (max_p - min_p) / min_p * 100
        pnl = amount * (max_p - min_p)
        
        text += f"\nСпред {min_ex}-{max_ex}: {spread:.2f}%"
        text += f"\nPnL: ${pnl:.2f}\n\nХвилини:"
        
        context.user_data["entry1"] = entry1
        context.user_data["entry2"] = entry2
        context.user_data["amount"] = amount
        context.user_data["symbol"] = symbol
        
        await update.message.reply_text(text)
        return INTERVAL
        
    except:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mins = int(update.message.text)
    uid = update.effective_user.id
    data = context.user_data.copy()
    data["interval"] = mins * 60
    
    data_store[uid] = data
    
    if uid in tasks_store:
        tasks_store[uid].cancel()
    
    app = context.application
    task = asyncio.create_task(run_monitor(uid, app))
    tasks_store[uid] = task
    
    await update.message.reply_text(f"{data['symbol']} {mins}хв запущено!")
    return ConversationHandler.END

async def run_monitor(uid, app):
    data = data_store.get(uid)
    while uid in tasks_store:
        try:
            prices = get_prices(data["symbol"])
            
            text = f"{data['symbol']} LIVE\n\n"
            min_p = 999999
            max_p = 0
            min_ex = ""
            max_ex = ""
            
            for ex, p in prices.items():
                text += f"{ex}: ${p}\n"
                if p < min_p:
                    min_p = p
                    min_ex = ex
                if p > max_p:
                    max_p = p
                    max_ex = ex
            
            pnl = data["amount"] * (max_p - min_p)
            text += f"\nСпред {min_ex}-{max_ex}: ${max_p-min_p}"
            text += f"\nPnL: ${pnl:.2f}"
            
            await app.bot.send_message(uid, text)
            await asyncio.sleep(data["interval"])
        except:
            await asyncio.sleep(60)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("Зупинено")
    else:
        await update.message.reply_text("Не запущено")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого немає")
        return
    
    data = data_store[uid]
    prices = get_prices(data["symbol"])
    
    text = f"{data['symbol']} STATUS\n\n"
    for ex, p in prices.items():
        text += f"{ex}: ${p}\n"
    
    await update.message.reply_text(text)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = "BTC"
    if context.args:
        symbol = context.args[0].upper()
    
    prices = get_prices(symbol)
    text = f"ТЕСТ {symbol}:\n\n"
    for ex, p in prices.items():
        text += f"{ex}: ${p}\n"
    
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

conv = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, start_monitor)],
    states={INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_interval)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv)
app.add_handler(CommandHandler("stop", stop_command))
app.add_handler(CommandHandler("status", status_command))
app.add_handler(CommandHandler("test", test_command))

print("Спред бот запущено!")
app.run_polling(drop_pending_updates=True)
