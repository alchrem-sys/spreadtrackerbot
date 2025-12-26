import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

PRICE1, EXCHANGE1, EXCHANGE2, INTERVAL = range(4)

data_store = {}
tasks_store = {}

def get_futures_price(exchange, symbol):
    """✅ ПРАЦЮЮЧІ ф'ючерсні API"""
    symbol_usdt = f"{symbol.upper()}USDT"
    
    try:
        if exchange == "binance":
            # ✅ ПРАЦЮЄ!
            r = requests.get("https://fapi.binance.com/fapi/v1/ticker/price", params={"symbol": symbol_usdt}, timeout=5)
            return float(r.json()["price"])
            
        elif exchange == "mexc":
            # MEXC USDT-M Futures (правильний ендпоінт)
            r = requests.get("https://contract.mexc.com/api/v1/contract/ticker", params={"symbol": symbol_usdt}, timeout=5)
            data = r.json()
            return float(data["data"][0]["lastPrice"]) if data.get("success") else None
            
        elif exchange == "bitget":
            # Bitget правильний формат
            r = requests.get("https://api.bitget.com/api/mix/v1/market/ticker", 
                           params={"symbol": f"{symbol}_USDT_UMCBL", "productType": "umcbl"}, timeout=5)
            data = r.json()
            if data.get("code") == "00000" and data.get("data"):
                return float(data["data"][0]["lastPr"])
                
        elif exchange == "gate":
            # Gate USDT Futures (список)
            r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=5)
            data = r.json()
            for ticker in 
                if ticker["contract"] == symbol_usdt:
                    return float(ticker["last"])
                    
        elif exchange == "bingx":
            # BingX правильний ендпоінт
            r = requests.get("https://open-api.bingx.com/openApi/swap/v2/ticker", params={"symbol": symbol_usdt}, timeout=5)
            data = r.json()
            if data.get("code") == 0 and data.get("data"):
                return float(data["data"][0]["lastPr"])
                
    except Exception as e:
        print(f"Error {exchange}: {e}")
        return None

def test_all_prices(symbol):
    """Тестує всі біржі"""
    results = {}
    for exchange in ["binance", "mexc", "bitget", "gate", "bingx"]:
        price = get_futures_price(exchange, symbol)
        results[exchange] = f"${price:.2f}" if price else "ERROR"
    return results

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Ф'ючерсний Спред Bot\n\n"
        "✅ BINANCE ПРАЦЮЄ!\n"
        "/test BTC - перевірити\n"
        "60000 60200 0.1 BTC"
    )
    return PRICE1

async def test_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = (context.args[0] if context.args else "BTC").upper()
    results = test_all_prices(symbol)
    text = f"🧪 Ф'ючерси {symbol}:\n\n" + "\n".join([f"{k.upper()}: {v}" for k,v in results.items()])
    await update.message.reply_text(text)

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4: 
        await update.message.reply_text("60000 60200 0.1 BTC")
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
        
        results = test_all_prices(symbol)
        test_text = "\n".join([f"{k}: {v}" for k,v in results.items()])
        
        await update.message.reply_text(
            f"✅ {symbol} | {amount} шт\n\n"
            f"API:\n{test_text}\n\n"
            "Біржа1 (binance/mexc/bitget/gate/bingx):"
        )
        return EXCHANGE1
    except:
        await update.message.reply_text("60000 60200 0.1 BTC")
        return PRICE1

async def exch1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ex1 = update.message.text.strip().lower()
    if ex1 not in ["binance", "mexc", "bitget", "gate", "bingx"]:
        await update.message.reply_text("binance/mexc/bitget/gate/bingx")
        return EXCHANGE1
    context.user_data["ex1"] = ex1
    await update.message.reply_text("Біржа2:")
    return EXCHANGE2

async def exch2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ex2 = update.message.text.strip().lower()
    if ex2 not in ["binance", "mexc", "bitget", "gate", "bingx"]:
        await update.message.reply_text("binance/mexc/bitget/gate/bingx")
        return EXCHANGE2
    context.user_data["ex2"] = ex2
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
        
        await update.message.reply_text(f"🚀 {data['sym']} запущено!\n{data['ex1']} ↔ {data['ex2']}\n{mins} хв")
        return ConversationHandler.END
    except:
        await update.message.reply_text("1-60!")
        return INTERVAL

async def run_monitor(uid, app):
    data = data_store[uid]
    while uid in tasks_store:
        try:
            p1 = get_futures_price(data["ex1"], data["sym"])
            p2 = get_futures_price(data["ex2"], data["sym"])
            
            if p1 and p2:
                pnl = data["amt"] * (p2 - p1)
                text = (
                    f"📊 {data['sym']} Ф'ючерси\n\n"
                    f"💱 {data['ex1'].upper()}: ${p1:.2f}\n"
                    f"💰 {data['ex2'].upper()}: ${p2:.2f}\n"
                    f"📈 Спред: {(p2-p1)/p1*100:.2f}%\n"
                    f"💵 PnL: ${pnl:+.2f}"
                )
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
    p1 = get_futures_price(data["ex1"], data["sym"])
    p2 = get_futures_price(data["ex2"], data["sym"])
    
    if p1 and p2:
        pnl = data["amt"] * (p2 - p1)
        text = (
            f"📋 {data['sym']} Статус\n"
            f"{data['ex1'].upper()}: ${p1:.2f}\n"
            f"{data['ex2'].upper()}: ${p2:.2f}\n"
            f"💵 PnL: ${pnl:+.2f}"
        )
        await update.message.reply_text(text)
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
    
    print("🚀 Ф'ючерсний бот v2!")
    app.run_polling()
