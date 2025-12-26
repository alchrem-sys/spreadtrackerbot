import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_all_prices(symbol):
    """Сканує всі біржі"""
    symbol_usdt = f"{symbol.upper()}USDT"
    prices = {}
    
    # BINANCE FUTURES
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["BINANCE_F"] = float(r.json()["price"])
    except:
        pass
    
    # MEXC SPOT
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["MEXC"] = float(r.json()["price"])
    except:
        pass
    
    # BITGET SPOT
    try:
        r = requests.get(f"https://api.bitget.com/api/spot/v1/market/ticker?symbol={symbol_usdt}", timeout=3)
        data = r.json()
        if data.get("code") == "00000":
            prices["BITGET"] = float(data["data"][0]["lastPr"])
    except:
        pass
    
    # GATE SPOT
    try:
        r = requests.get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol_usdt}", timeout=3)
        data = r.json()
        if 
            prices["GATE"] = float(data[0]["last"])
    except:
        pass
    
    return prices

async def handle_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    
    try:
        entry1 = float(parts[0])
        entry2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        prices = get_all_prices(symbol)
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if len(valid_prices) < 2:
            await update.message.reply_text(f"❌ {symbol} мало цін. Спробуй BTC")
            return ConversationHandler.END
        
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        min_ex = next(k for k, v in valid_prices.items() if v == min_price)
        max_ex = next(k for k, v in valid_prices.items() if v == max_price)
        
        spread = (max_price - min_price) / min_price * 100
        pnl = amount * (max_price - min_price)
        
        text = f"🔥 {symbol} СПРЕД\n\n"
        text += f"Вхід: ${entry1:,.0f} → ${entry2:,.0f}\n"
        text += f"{amount} шт\n\n"
        text += "ЦІНИ:\n"
        
        for ex, p in prices.items():
            status = f"${p:,.0f}" if p else "❌"
            text += f"{ex:<10}: {status}\n"
        
        text += f"\nСПРЕД:\n"
        text += f"Купити {min_ex}: ${min_price:,.0f}\n"
        text += f"Продати {max_ex}: ${max_price:,.0f}\n"
        text += f"Спред: {spread:.2f}%\n"
        text += f"PnL: ${pnl:,.2f}\n\n"
        text += "Хвилини:"
        
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
    try:
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
        
        await update.message.reply_text(f"🚀 {data['symbol']} {mins}хв!\n/status /stop")
        return ConversationHandler.END
    except:
        await update.message.reply_text("1-60")
        return INTERVAL

async def run_monitor(uid, app):
    data = data_store.get(uid)
    if not 
        return
        
    while uid in tasks_store:
        try:
            prices = get_all_prices(data["symbol"])
            valid_prices = {k: v for k, v in prices.items() if v is not None}
            
            if len(valid_prices) >= 2:
                min_p = min(valid_prices.values())
                max_p = max(valid_prices.values())
                min_ex = next(k for k, v in valid_prices.items() if v == min_p)
                max_ex = next(k for k, v in valid_prices.items() if v == max_p)
                
                pnl = data["amount"] * (max_p - min_p)
                
                text = f"🔥 {data['symbol']} LIVE\n\n"
                for ex, p in prices.items():
                    status = f"${p:,.0f}" if p else "❌"
                    text += f"{ex:<10}: {status}\n"
                
                text += f"\nСПРЕД:\n"
                text += f"{min_ex}: ${min_p:,.0f}\n"
                text += f"{max_ex}: ${max_p:,.0f}\n"
                text += f"PnL: ${pnl:,.2f}"
                
                await app.bot.send_message(uid, text)
            
            await asyncio.sleep(data["interval"])
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(60)

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("🛑 ЗУПИНЕНО")
    else:
        await update.message.reply_text("Не запущено")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого немає")
        return
    
    data = data_store[uid]
    prices = get_all_prices(data["symbol"])
    
    text = f"📋 {data['symbol']} STATUS\n\n"
    for ex, p in prices.items():
        status = f"${p:,.0f}" if p else "❌"
        text += f"{ex:<10}: {status}\n"
    
    valid = {k: v for k, v in prices.items() if v is not None}
    if len(valid) >= 2:
        min_p = min(valid.values())
        max_p = max(valid.values())
        pnl = data["amount"] * (max_p - min_p)
        text += f"\nPnL: ${pnl:,.2f}"
    
    await update.message.reply_text(text)

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = (context.args[0] if context.args else "BTC").upper()
    prices = get_all_prices(symbol)
    
    text = f"🧪 {symbol}:\n\n"
    for ex, p in prices.items():
        status = f"${p:,.0f}" if p else "❌"
        text += f"{ex:<10}: {status}\n"
    
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prices)],
        states={INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_interval)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test_all))
    app.add_handler(CommandHandler("stop", stop_monitor))
    app.add_handler(CommandHandler("status", show_status))
    
    print("🚀 Спред Бот - ФІНАЛЬНА ВЕРСІЯ!")
    app.run_polling(drop_pending_updates=True)
