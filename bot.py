import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_all_futures_prices(symbol):
    """Бере ціну з ВСІХ бірж одразу"""
    symbol_usdt = f"{symbol.upper()}USDT"
    prices = {}
    
    # BINANCE FUTURES (100% працює)
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["BINANCE"] = float(r.json()["price"])
    except:
        prices["BINANCE"] = None
    
    # MEXC FUTURES
    try:
        r = requests.get("https://contract.mexc.com/api/v1/contract/ticker", params={"symbol": symbol_usdt}, timeout=3)
        data = r.json()
        prices["MEXC"] = float(data["data"][0]["lastPrice"]) if data.get("success") else None
    except:
        prices["MEXC"] = None
    
    # BITGET FUTURES
    try:
        r = requests.get("https://api.bitget.com/api/mix/v1/market/ticker", params={"symbol": f"{symbol}_USDT_UMCBL"}, timeout=3)
        data = r.json()
        prices["BITGET"] = float(data["data"][0]["lastPr"]) if data.get("code") == "00000" else None
    except:
        prices["BITGET"] = None
    
    # GATE FUTURES
    try:
        r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=3)
        data = r.json()
        for ticker in 
            if ticker["contract"] == symbol_usdt:
                prices["GATE"] = float(ticker["last"])
                break
    except:
        prices["GATE"] = None
    
    # BINGX FUTURES
    try:
        r = requests.get(f"https://open-api.bingx.com/openApi/swap/v2/ticker?symbol={symbol_usdt}", timeout=3)
        data = r.json()
        prices["BINGX"] = float(data["data"][0]["lastPr"]) if data.get("code") == 0 else None
    except:
        prices["BINGX"] = None
    
    return prices

async def handle_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    
    try:
        entry_price1 = float(parts[0])
        entry_price2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        # Беремо поточні ціни з ВСІХ бірж
        prices = get_all_futures_prices(symbol)
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if not valid_prices:
            await update.message.reply_text(f"❌ {symbol} немає на жодній біржі")
            return ConversationHandler.END
        
        # Знаходимо найкращу пару для спреду
        price_list = list(valid_prices.values())
        min_price = min(price_list)
        max_price = max(price_list)
        min_exchange = [k for k, v in valid_prices.items() if v == min_price][0]
        max_exchange = [k for k, v in valid_prices.items() if v == max_price][0]
        
        current_spread = (max_price - min_price) / min_price * 100
        current_pnl = amount * (max_price - min_price)
        
        # Формуємо повідомлення
        text = f"🔥 {symbol} Ф'ЮЧЕРСИ СПРЕД\n\n"
        text += f"📈 Вхід: ${entry_price1} → ${entry_price2}\n"
        text += f"💰 {amount} шт | PnL: ${current_pnl:+,.2f}\n\n"
        
        text += "💹 ПОТОЧНІ ЦІНИ:\n"
        for exch, price in prices.items():
            status = f"${price:,.0f}" if price else "❌"
            text += f"{exch}: {status}\n"
        
        text += f"\n🎯 НАЙКРАЩИЙ СПРЕД:\n"
        text += f"Купити {min_exchange}: ${min_price:,.0f}\n"
        text += f"Продати {max_exchange}: ${max_price:,.0f}\n"
        text += f"📊 Спред: {current_spread:.2f}%\n"
        text += f"💵 PnL: ${current_pnl:+,.2f}\n\n"
        text += "⏰ Хвилини для моніторингу (1-60):"
        
        context.user_data.clear()
        context.user_data.update({
            "entry1": entry_price1, "entry2": entry_price2, 
            "amt": amount, "sym": symbol
        })
        
        await update.message.reply_text(text)
        return INTERVAL
        
    except:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END

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
        
        await update.message.reply_text(f"🚀 СПРЕД МОНІТОРИНГ!\n{symbol} | {mins} хв\n/status /stop")
        return ConversationHandler.END
    except:
        await update.message.reply_text("1-60")
        return INTERVAL

async def run_monitor(uid, app):
    data = data_store[uid]
    while uid in tasks_store:
        try:
            prices = get_all_futures_prices(data["sym"])
            valid_prices = {k: v for k, v in prices.items() if v is not None}
            
            if len(valid_prices) >= 2:
                price_list = list(valid_prices.values())
                min_price = min(price_list)
                max_price = max(price_list)
                min_exchange = [k for k, v in valid_prices.items() if v == min_price][0]
                max_exchange = [k for k, v in valid_prices.items() if v == max_price][0]
                
                current_spread = (max_price - min_price) / min_price * 100
                current_pnl = data["amt"] * (max_price - min_price)
                
                text = f"🔥 {data['sym']} СПРЕД LIVE\n\n"
                for exch, price in prices.items():
                    status = f"${price:,.0f}" if price else "❌"
                    text += f"{exch}: {status}\n"
                
                text += f"\n🎯 НАЙКРАЩЕ:\n"
                text += f"Купити {min_exchange}: ${min_price:,.0f}\n"
                text += f"Продати {max_exchange}: ${max_price:,.0f}\n"
                text += f"📈 Спред: {current_spread:.2f}%\n"
                text += f"💵 PnL: ${current_pnl:+,.2f}"
                
                await app.bot.send_message(uid, text)
            else:
                await app.bot.send_message(uid, f"❌ {data['sym']} мало даних")
            
            await asyncio.sleep(data["sec"])
        except:
            await asyncio.sleep(60)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("🛑 СПРЕД ЗУПИНЕНО")
    else:
        await update.message.reply_text("Не запущено")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого немає")
        return
    
    data = data_store[uid]
    prices = get_all_futures_prices(data["sym"])
    valid_prices = {k: v for k, v in prices.items() if v is not None}
    
    if len(valid_prices) >= 2:
        price_list = list(valid_prices.values())
        min_price = min(price_list)
        max_price = max(price_list)
        current_pnl = data["amt"] * (max_price - min_price)
        
        text = f"📋 {data['sym']} СПРЕД STATUS\n\n"
        for exch, price in prices.items():
            status = f"${price:,.0f}" if price else "❌"
            text += f"{exch}: {status}\n"
        text += f"\n💵 PnL: ${current_pnl:+,.2f}"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("❌ Недостатньо даних")

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = (context.args[0] if context.args else "BTC").upper()
    prices = get_all_futures_prices(symbol)
    text = f"🧪 {symbol} ВСІ БІРЖІ:\n\n"
    for exch, price in prices.items():
        status = f"${price:,.0f}" if price else "❌"
        text += f"{exch}: {status}\n"
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prices)],
        states={
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test_all))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    print("🚀 СПРЕД З ВСІХ БІРЖ!")
    app.run_polling()
