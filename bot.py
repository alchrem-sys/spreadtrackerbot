import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_prices(symbol):
    symbol_usdt = f"{symbol.upper()}USDT"
    prices = {}
    
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["BINANCE"] = float(r.json()["price"])
    except:
        pass
    
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["MEXC"] = float(r.json()["price"])
    except:
        pass
    
    return prices

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if len(valid_prices) < 2:
            await update.message.reply_text(f"{symbol} мало цін")
            return ConversationHandler.END
        
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        min_ex = [k for k, v in valid_prices.items() if v == min_price][0]
        max_ex = [k for k, v in valid_prices.items() if v == max_price][0]
        
        spread = (max_price - min_price) / min_price * 100
        pnl = amount * (max_price - min_price)
        
        text = f"{symbol} СПРЕД\n\n"
        text += f"Вхід: ${entry1} → ${entry2}\n"
        text += f"{amount} шт\n\n"
        
        for ex, p in prices.items():
            status = f"${p}" if p else "❌"
            text += f"{ex}: {status}\n"
        
        text += f"\nСпред {min_ex}-{max_ex}: {spread:.2f}%\n"
        text += f"PnL: ${pnl}\n\nХвилини:"
        
        context.user_data["entry1"] = entry1
        context.user_data["entry2"] = entry2
        context.user_data["amount"] = amount
        context.user_data["symbol"] = symbol
        
        await update.message.reply_text(text)
        return INTERVAL
        
    except:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mins = int(update.message.text)
        uid = update.effective_user.id
        data = context.user_data.copy()
        data["time"] = mins * 60
        
        data_store[uid] = data
        
        if uid in tasks_store:
            tasks_store[uid].cancel()
        
        app = context.application
        task = asyncio.create_task(run_check(uid, app))
        tasks_store[uid] = task
        
        await update.message.reply_text(f"{data['symbol']} {mins}хв запущено!")
        return ConversationHandler.END
    except:
        await update.message.reply_text("1-60")
        return INTERVAL

async def run_check(uid, app):
    data = data_store.get(uid)
    while uid in tasks_store:
        try:
            prices = get_prices(data["symbol"])
            valid_prices = {k: v for k, v in prices.items() if v is not None}
            
            if len(valid_prices) >= 2:
                min_p = min(valid_prices.values())
                max_p = max(valid_prices.values())
                min_ex = [k for k, v in valid_prices.items() if v == min_p][0]
                max_ex = [k for k, v in valid_prices.items() if v == max_p][0]
                
                pnl = data["amount"] * (max_p - min_p)
                
                text = f"{data['symbol']} LIVE\n\n"
                for ex, p in prices.items():
                    status = f"${p}" if p else "❌"
                    text += f"{ex}: {status}\n"
                
                text += f"\nСпред {min_ex}-{max_ex}: ${max_p-min_p}"
                text += f"\nPnL: ${pnl}"
                
                await app.bot.send_message(uid, text)
            
            await asyncio.sleep(data["time"])
        except:
            await asyncio.sleep(60)

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("Зупинено")
    else:
        await update.message.reply_text("Не запущено")

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого немає")
        return
    
    data = data_store[uid]
    prices = get_prices(data["symbol"])
    
    text = f"{data['symbol']} INFO\n\n"
    for ex, p in prices.items():
        status = f"${p}" if p else "❌"
        text += f"{ex}: {status}\n"
    
    await update.message.reply_text(text)

async def test_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = "BTC"
    if context.args:
        symbol = context.args[0].upper()
    
    prices = get_prices(symbol)
    text = f"ТЕСТ {symbol}:\n\n"
    for ex, p in prices.items():
        status = f"${p}" if p else "❌"
        text += f"{ex}: {status}\n"
    
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT
