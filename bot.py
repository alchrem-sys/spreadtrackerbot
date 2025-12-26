import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

EXCHANGE1, EXCHANGE2, INTERVAL = range(3)

data_store = {}
tasks_store = {}

def get_futures_price(exchange, symbol):
    """ВСІ 5 ф'ючерсних бірж - ПРАВИЛЬНІ ендпоінти"""
    symbol_upper = symbol.upper()
    
    try:
        # 🔥 BINANCE FUTURES
        if exchange == "binance":
            r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_upper}USDT", timeout=5)
            return float(r.json()["price"])
        
        # 🔥 MEXC FUTURES
        elif exchange == "mexc":
            r = requests.get(f"https://contract.mexc.com/api/v1/contract/ticker?symbol={symbol_upper}USDT", timeout=5)
            data = r.json()
            return float(data["data"][0]["lastPrice"]) if data.get("success") else None
        
        # 🔥 BITGET FUTURES (виправлений)
        elif exchange == "bitget":
            r = requests.get("https://api.bitget.com/api/mix/v1/market/ticker", 
                           params={"symbol": f"{symbol_upper}_USDT_UMCBL"}, timeout=5)
            data = r.json()
            return float(data["data"][0]["lastPr"]) if data.get("code") == "00000" else None
        
        # 🔥 GATE FUTURES (виправлений)
        elif exchange == "gate":
            r = requests.get("https://fx-api.gateio.ws/api/v4/futures/usdt/tickers", params={"contract": f"{symbol_upper}USDT"}, timeout=5)
            data = r.json()
            return float(data[0]["last"]) if data else None
        
        # 🔥 BINGX FUTURES (виправлений)
        elif exchange == "bingx":
            r = requests.get(f"https://open-api.bingx.com/openApi/swap/v2/ticker?symbol={symbol_upper}USDT", timeout=5)
            data = r.json()
            return float(data["data"][0]["lastPr"]) if data.get("code") == 0 else None
        
    except:
        return None

def test_all_futures(symbol):
    """Тестує ВСІ 5 бірж"""
    results = {}
    exchanges = ["binance", "mexc", "bitget", "gate", "bingx"]
    for exchange in exchanges:
        price = get_futures_price(exchange, symbol)
        results[exchange] = f"${price:,.0f}" if price else "❌"
    return results

async def handle_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return EXCHANGE1
    
    try:
        price1 = float(parts[0])
        price2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        context.user_data.clear()
        context.user_data.update({
            "p1": price1, "p2": price2, "amt": amount, "sym": symbol
        })
        
        results = test_all_futures(symbol)
        test_text = "\n".join([f"{k.upper()}: {v}" for k,v in results.items()])
        
        await update.message.reply_text(
            f"🔥 {symbol} Ф'ЮЧЕРСИ | {amount} шт\n\n"
            f"ВСІ 5 БІРЖ:\n{test_text}\n\n"
            "Біржа1 (binance/mexc/bitget/gate/bingx):"
        )
        return EXCHANGE1
    except:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return EXCHANGE1

async def exch1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ex1 = update.message.text.strip().lower()
    valid = ["binance", "mexc", "bitget", "gate", "bingx"]
    if ex1 not in valid:
        await update.message.reply_text("binance/mexc/bitget/gate/bingx")
        return EXCHANGE1
    context.user_data["ex1"] = ex1
    await update.message.reply_text("Біржа2:")
    return EXCHANGE2

async def exch2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ex2 = update.message.text.strip().lower()
    valid = ["binance", "mexc", "bitget", "gate", "bingx"]
    if ex2 not in valid:
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
        
        await update.message.reply_text(
            f"🚀 Ф'ЮЧЕРСНИЙ СПРЕД!\n\n"
            f"🪙 {data['sym']}\n"
            f"💱 {data['ex1'].upper()} ↔ {data['ex2'].upper()}\n"
            f"⏰ {mins} хв\n\n/status /stop"
        )
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
                spread_pct = (p2 - p1) / p1 * 100
                text = (
                    f"🔥 {data['sym']} Ф'ЮЧЕРСИ LIVE\n\n"
                    f"💱 {data['ex1'].upper()}: ${p1:,.0f}\n"
                    f"💰 {data['ex2'].upper()}: ${p2:,.0f}\n\n"
                    f"📈 СПРЕД: {spread_pct:+.2f}%\n"
                    f"💵 PnL: ${pnl:+,.2f}"
                )
                await app.bot.send_message(uid, text)
            else:
                await app.bot.send_message(uid, f"❌ {data['sym']} оффлайн")
            
            await asyncio.sleep(data["sec"])
        except:
            await asyncio.sleep(60)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("🛑 ЗУПИНЕНО")
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
        await update.message.reply_text(
            f"📋 {data['sym']} Ф'ЮЧЕРСИ\n"
            f"{data['ex1'].upper()}: ${p1:,.0f}\n"
            f"{data['ex2'].upper()}: ${p2:,.0f}\n"
            f"💵 PnL: ${pnl:+,.2f}"
        )
    else:
        await update.message.reply_text("❌ Ф'ючерси оффлайн")

async def test_futures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = (context.args[0] if context.args else "BTC").upper()
    results = test_all_futures(symbol)
    text = f"🔥 ВСІ Ф'ЮЧЕРСИ {symbol}:\n\n" + "\n".join([f"{k.upper()}: {v}" for k,v in results.items()])
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prices)],
        states={
            EXCHANGE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, exch1)],
            EXCHANGE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, exch2)],
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test_futures))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    print("🚀 ВСІ 5 Ф'ЮЧЕРСНИХ БІРЖ!")
    app.run_polling()
