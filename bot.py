import os
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

logging.basicConfig(level=logging.INFO)

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_all_futures_prices(symbol):
    """Ціни з ВСІХ бірж"""
    symbol_usdt = f"{symbol.upper()}USDT"
    prices = {}
    
    # BINANCE FUTURES
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["BINANCE"] = float(r.json()["price"])
    except:
        prices["BINANCE"] = None
    
    # MEXC SPOT (стабільний)
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["MEXC"] = float(r.json()["price"])
    except:
        prices["MEXC"] = None
    
    # BITGET SPOT
    try:
        r = requests.get(f"https://api.bitget.com/api/spot/v1/market/ticker?symbol={symbol_usdt}", timeout=3)
        data = r.json()
        prices["BITGET"] = float(data["data"][0]["lastPr"]) if data.get("code") == "00000" else None
    except:
        prices["BITGET"] = None
    
    # GATE SPOT
    try:
        r = requests.get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol_usdt}", timeout=3)
        data = r.json()
        prices["GATE"] = float(data[0]["last"]) if data else None
    except:
        prices["GATE"] = None
    
    # BINGX SPOT
    try:
        r = requests.get(f"https://open-api.bingx.com/openApi/spot/v1/market/ticker?symbol={symbol_usdt}", timeout=3)
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
        
        prices = get_all_futures_prices(symbol)
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if not valid_prices:
            await update.message.reply_text(f"❌ {symbol} немає цін")
            return ConversationHandler.END
        
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        min_exchange = next(k for k, v in valid_prices.items() if v == min_price)
        max_exchange = next(k for k, v in valid_prices.items() if v == max_price)
        
        current_spread = (max_price - min_price) / min_price * 100
        current_pnl = amount * (max_price - min_price)
        
        text = f"🔥 {symbol} СПРЕД\n\n"
        text += f"📈 Вхід: ${entry_price1} → ${entry_price2}\n"
        text += f"💰 {amount} шт\n\n"
        
        text += "💹 ЦІНИ:\n"
        for exch, price in prices.items():
            status = f"${price:,.0f}" if price else "❌"
            text += f"{exch:<8}: {status}\n"
        
        text += f"\n🎯 НАЙКРАЩЕ:\n"
        text += f"КУПИТИ {min_exchange}:  ${min_price:,.0f}\n"
        text += f"ПРОДАТИ {max_exchange}: ${max_price:,.0f}\n"
        text += f"📊 СПРЕД: {current_spread:.2f}%\n"
        text += f"💵 PnL: ${current_pnl:,.2f}\n\n"
        text += "⏰ Хвилини (1-60):"
        
        context.user_data.update({
            "entry1": entry_price1, "entry2": entry_price2, 
            "amt": amount, "sym": symbol
        })
        
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
        data["sec"] = mins * 60
        
        data_store[uid] = data
        
        # Зупиняємо попередню задачу
        if uid in tasks_store:
            tasks_store[uid].cancel()
        
        app = context.application
        task = asyncio.create_task(run_monitor(uid, app))
        tasks_store[uid] = task
        
        await update.message.reply_text(
            f"🚀 СПРЕД МОНИТОРИНГ!\n\n"
            f"🪙 {data['sym']} | {mins} хв\n"
            f"/status /stop /test {data['sym']}"
        )
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
                min_price = min(valid_prices.values())
                max_price = max(valid_prices.values())
                min_exchange = next(k for k, v in valid_prices.items() if v == min_price)
                max_exchange = next(k for k, v in valid_prices.items() if v == max_price)
                
                current_pnl = data["amt"] * (max_price - min_price)
                
                text = f"🔥 {data['sym']} LIVE СПРЕД\n\n"
                for exch, price in prices.items():
                    status = f"${price:,.0f}" if price else "❌"
                    text += f"{exch:<8}: {status}\n"
                
                text += f"\n🎯 СПРЕД:\n"
                text += f"КУПИТИ {min_exchange}: ${min_price:,.0f}\n"
                text += f"ПРОДАТИ {max_exchange}: ${max_price:,.0f}\n"
                text += f"💵 PnL: ${current_pnl:,.2f}"
                
                await app.bot.send_message(uid, text)
            
            await asyncio.sleep(data["sec"])
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(60)

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        if uid in data_store:
            del data_store[uid]
        await update.message.reply_text("🛑 СПРЕД ЗУПИНЕНО")
    else:
        await update.message.reply_text("Нічого не запущено")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого не запущено")
        return
    
    data = data_store[uid]
    prices = get_all_futures_prices(data["sym"])
    
    text = f"📋 {data['sym']} STATUS\n\n"
    for exch, price in prices.items():
        status = f"${price:,.0f}" if price else "❌"
        text += f"{exch:<8}: {status}\n"
    
    valid_prices = {k: v for k, v in prices.items() if v is not None}
    if len(valid_prices) >= 2:
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        pnl = data["amt"] * (max_price - min_price)
        text += f"\n💵 Поточний PnL: ${pnl:,.2f}"
    
    await update.message.reply_text(text)

async def test_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    # Захист від подвійного запуску
    if os.getenv("DYNO"):
        print("🚀 Railway Production Bot")
    
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prices)],
        states={
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test_prices))
    app.add_handler(CommandHandler("stop", stop_monitor))
    app.add_handler(CommandHandler("status", show_status))
    
    print("🚀 СПРЕД Бот запущено!")
    app.run_polling(drop_pending_updates=True)  # 🔧 РІЗИК Конфліктів!
