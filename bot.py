import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_all_futures_prices(symbol):
    """ПРАВИЛЬНІ ф'ючерсні API з документації"""
    symbol_usdt = f"{symbol.upper()}USDT"
    prices = {}
    
    # ✅ BINANCE FUTURES (працює)
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["BINANCE"] = float(r.json()["price"])
    except:
        prices["BINANCE"] = None
    
    # ✅ MEXC FUTURES (правильний ендпоінт з docs)
    try:
        r = requests.get("https://contract.mexc.com/api/v1/contract/ticker", params={"symbol": symbol_usdt}, timeout=3)
        data = r.json()
        if data.get("success") and data.get("data"):
            prices["MEXC"] = float(data["data"][0]["lastPrice"])
    except:
        prices["MEXC"] = None
    
    # ✅ BITGET FUTURES (з docs: /api/mix/v1/market/tickers)
    try:
        r = requests.get("https://api.bitget.com/api/mix/v1/market/tickers", params={"productType": "umcbl"}, timeout=3)
        data = r.json()
        if data.get("code") == "00000" and data.get("data"):
            for ticker in data["data"]:
                if ticker["symbol"].endswith("_USDT_UMCBL"):
                    base = ticker["symbol"].split("_")[0]
                    if base == symbol.upper():
                        prices["BITGET"] = float(ticker["lastPr"])
                        break
    except:
        prices["BITGET"] = None
    
    # ✅ GATE FUTURES USDT (з docs: /futures/usdt/tickers)
    try:
        r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=3)
        data = r.json()
        for ticker in 
            if ticker["contract"] == symbol_usdt:
                prices["GATE"] = float(ticker["last"])
                break
    except:
        prices["GATE"] = None
    
    # ✅ BINGX FUTURES (з docs: swap/v2/ticker)
    try:
        r = requests.get("https://open-api.bingx.com/openApi/swap/v2/ticker", params={"symbol": symbol_usdt}, timeout=3)
        data = r.json()
        if data.get("code") == 0 and data.get("data"):
            prices["BINGX"] = float(data["data"][0]["lastPr"])
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
        
        prices = get_all_futures_prices(symbol)
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if not valid_prices:
            await update.message.reply_text(f"❌ {symbol} немає на біржах")
            return ConversationHandler.END
        
        # Знаходимо найкращий спред
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        min_exchange = next(k for k, v in valid_prices.items() if v == min_price)
        max_exchange = next(k for k, v in valid_prices.items() if v == max_price)
        
        current_spread_pct = (max_price - min_price) / min_price * 100
        current_pnl = amount * (max_price - min_price)
        
        text = f"🔥 {symbol} Ф'ЮЧЕРСИ | {amount} шт\n\n"
        text += f"Вхід: ${entry_price1:,.0f} → ${entry_price2:,.0f}\n\n"
        text += "💹 ЦІНИ:\n"
        
        for exch, price in prices.items():
            status = f"${price:,.0f}" if price else "❌"
            text += f"{exch:<8}: {status}\n"
        
        text += f"\n🎯 НАЙКРАЩИЙ СПРЕД:\n"
        text += f"🟢 Купити {min_exchange}: ${min_price:,.0f}\n"
        text += f"🔴 Продати {max_exchange}: ${max_price:,.0f}\n"
        text += f"📊 Спред: {current_spread_pct:.2f}%\n"
        text += f"💵 PnL: ${current_pnl:,.2f}\n\n"
        text += "⏰ Моніторинг (хвилин):"
        
        context.user_data.update({
            "entry1": entry_price1, "entry2": entry_price2, 
            "amt": amount, "sym": symbol
        })
        
        await update.message.reply_text(text)
        return INTERVAL
        
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}\n87000 87200 0.1 BTC")
        return ConversationHandler.END

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mins = int(update.message.text)
        if mins < 1 or mins > 60:
            await update.message.reply_text("1-60 хвилин!")
            return INTERVAL
            
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
            f"🚀 МОНІТОРИНГ СПРЕДУ!\n\n"
            f"🪙 {data['sym']} | {mins} хв\n"
            f"/status /stop /test {data['sym']}"
        )
        return ConversationHandler.END
    except:
        await update.message.reply_text("Введи 1-60")
        return INTERVAL

async def run_monitor(uid, app):
    data = data_store.get(uid)
    if not 
        return
        
    while uid in tasks_store:
        try:
            prices = get_all_futures_prices(data["sym"])
            valid_prices = {k: v for k, v in prices.items() if v is not None}
            
            if len(valid_prices) >= 2:
                min_price = min(valid_prices.values())
                max_price = max(valid_prices.values())
                min_exchange = next(k for k, v in valid_prices.items() if v == min_price)
                max_exchange = next(k for k, v in valid_prices.items() if v == max_price)
                
                pnl = data["amt"] * (max_price - min_price)
                
                text = f"🔥 {data['sym']} LIVE СПРЕД\n\n"
                for exch, price in prices.items():
                    status = f"${price:,.0f}" if price else "❌"
                    text += f"{exch:<8}: {status}\n"
                
                text += f"\n🎯 СПРЕД:\n"
                text += f"🟢 {min_exchange:<8}: ${min_price:,.0f}\n"
                text += f"🔴 {max_exchange:<8}: ${max_price:,.0f}\n"
                text += f"💵 PnL: ${pnl:,.2f}"
                
                await app.bot.send_message(uid, text)
            else:
                await app.bot.send_message(uid, f"❌ {data['sym']} мало бірж онлайн")
            
            await asyncio.sleep(data["sec"])
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(60)

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("🛑 СПРЕД ЗУПИНЕНО")
    else:
        await update.message.reply_text("Нічого не запущено")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого не моніториться")
        return
    
    data = data_store[uid]
    prices = get_all_futures_prices(data["sym"])
    
    text = f"📋 {data['sym']} СПРЕД STATUS\n\n"
    for exch, price in prices.items():
        status = f"${price:,.0f}" if price else "❌"
        text += f"{exch:<8}: {status}\n"
    
    valid_prices = {k: v for k, v in prices.items() if v is not None}
    if len(valid_prices) >= 2:
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        pnl = data["amt"] * (max_price - min_price)
        text += f"\n💵 PnL: ${pnl:,.2f}"
    
    await update.message.reply_text(text)

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = (context.args[0] if context.args else "BTC").upper()
    prices = get_all_futures_prices(symbol)
    
    text = f"🧪 {symbol} ВСІ БІРЖІ:\n\n"
    for exch, price in prices.items():
        status = f"${price:,.0f}" if price else "❌"
        text += f"{exch:<8}: {status}\n"
    
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prices)],
        states={
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test_all))
    app.add_handler(CommandHandler("stop", stop_monitor))
    app.add_handler(CommandHandler("status", show_status))
    
    print("🚀 Ф'ючерсний Спред Бот v3.0!")
    app.run_polling(drop_pending_updates=True)
