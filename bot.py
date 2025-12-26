import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

PRICE1, EXCHANGE1, EXCHANGE2, INTERVAL = range(4)

data_store = {}
tasks_store = {}

def test_all_prices(symbol):
    """Тестує всі біржі одразу"""
    results = {}
    symbol_usdt = f"{symbol.upper()}USDT"
    
    try:
        # MEXC
        r = requests.get("https://api.mexc.com/api/v3/ticker/price", params={"symbol": symbol_usdt}, timeout=3)
        results["mexc"] = r.json().get("price", "ERROR")
    except:
        results["mexc"] = "FAIL"
    
    try:
        # Binance
        r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol_usdt}, timeout=3)
        results["binance"] = r.json().get("price", "ERROR")
    except:
        results["binance"] = "FAIL"
    
    return results

def get_price(exchange, symbol):
    symbol_usdt = f"{symbol.upper()}USDT"
    try:
        if exchange == "mexc":
            r = requests.get("https://api.mexc.com/api/v3/ticker/price", params={"symbol": symbol_usdt}, timeout=5)
            data = r.json()
            return float(data["price"]) if "price" in data else None
        elif exchange == "binance":
            r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol_usdt}, timeout=5)
            data = r.json()
            return float(data["price"]) if "price" in data else None
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Спред бот\n\n/test BTC - перевірити API\nабо\nціна1 ціна2 токени символ")
    return PRICE1

async def test_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test для діагностики"""
    if context.args:
        symbol = context.args[0].upper()
        results = test_all_prices(symbol)
        text = f"🧪 Тест {symbol}:\n\n"
        for exch, price in results.items():
            text += f"{exch}: {price}\n"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Використай /test BTC")

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4: 
        await update.message.reply_text("Формат: 60000 60200 0.1 BTC\nСпочатку перевір /test BTC")
        return PRICE1
    
    try:
        price1 = float(parts[0])
        price2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        context.user_data.clear()
        context.user_data.update({
            "p1": price1, "p2": price2, "amt": amount, "sym": symbol
        })
        
        # Тестуємо API одразу
        test_results = test_all_prices(symbol)
        test_text = "📊 API тест:\n" + "\n".join([f"{k}: {v}" for k,v in test_results.items()])
        
        await update.message.reply_text(
            f"✅ {symbol}\nТокенів: {amount}\n\n{test_text}\n\nБіржа1 (mexc/binance):"
        )
        return EXCHANGE1
    except:
        await update.message.reply_text("Помилка! Приклад: 60000 60200 0.1 BTC")
        return PRICE1

async def exch1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ex1"] = update.message.text.strip().lower()
    await update.message.reply_text("Біржа2 (mexc/binance):")
    return EXCHANGE2

async def exch2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ex2"] = update.message.text.strip().lower()
    await update.message.reply_text("Хвилини (1-60):")
    return INTERVAL

async def interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
        
        await update.message.reply_text(f"🚀 Запущено! {mins} хв\n/status /stop")
        return ConversationHandler.END
    except:
        await update.message.reply_text("Число 1-60!")
        return INTERVAL

async def run_monitor(uid, app):
    data = data_store[uid]
    while uid in tasks_store:
        try:
            p1 = get_price(data["ex1"], data["sym"])
            p2 = get_price(data["ex2"], data["sym"])
            
            if p1 and p2:
                pnl = data["amt"] * (p2 - p1)
                text = f"📊 {data['sym']}\n{data['ex1'].upper()}: ${p1:.4f}\n{data['ex2'].upper()}: ${p2:.4f}\n💵 PnL: ${pnl:+.2f}"
                await app.bot.send_message(uid, text)
            else:
                await app.bot.send_message(uid, f"❌ {data['sym']} немає ціни")
            
            await asyncio.sleep(data["sec"])
        except:
            await asyncio.sleep(60)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("🛑 Зупинено")
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
            f"📋 {data['sym']}\n"
            f"{data['ex1'].upper()}: ${p1:.4f}\n"
            f"{data['ex2'].upper()}: ${p2:.4f}\n"
            f"💵 PnL: ${pnl:+.2f}"
        )
    else:
        await update.message.reply_text("❌ Ціни немає")

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
    app.add_handler(CommandHandler("test", test_api))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    print("🚀 Бот з тестом запущено!")
    app.run_polling()
