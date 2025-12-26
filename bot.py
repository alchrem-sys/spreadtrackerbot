import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_token_price(symbol):
    """Ціна з кількох бірж для будь-якого токена"""
    symbol_usdt = f"{symbol.upper()}USDT"
    prices = {}
    
    # Binance Futures
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["BinanceF"] = float(r.json()["price"])
    except:
        pass
    
    # MEXC Spot
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["MEXC"] = float(r.json()["price"])
    except:
        pass
    
    # Gate.io Spot
    try:
        r = requests.get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol_usdt}", timeout=3)
        data = r.json()
        prices["Gate"] = float(data[0]["last"]) if data else None
    except:
        pass
    
    return prices

async def test_all_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /test TOKEN - показує ціни з бірж для будь-якого токена"""
    if not context.args:
        await update.message.reply_text("Використай: /test sol, /test pepe, /test bonk")
        return
    
    symbol = context.args[0].upper()
    prices = get_token_price(symbol)
    
    if not prices:
        await update.message.reply_text(f"❌ {symbol} не знайдено на біржах")
        return
    
    text = f"🧪 {symbol} - ЦІНИ:\n\n"
    min_price = min(prices.values())
    max_price = max(prices.values())
    min_ex = min(prices, key=prices.get)
    max_ex = max(prices, key=prices.get)
    
    for exchange, price in prices.items():
        text += f"{exchange:<10}: ${price:.6f}\n"
    
    spread = (max_price - min_price) / min_price * 100
    text += f"\n🎯 СПРЕД:\n"
    text += f"🟢 Купити {min_ex}: ${min_price:.6f}\n"
    text += f"🔴 Продати {max_ex}: ${max_price:.6f}\n"
    text += f"📊 Спред: {spread:.2f}%"
    
    await update.message.reply_text(text)

async def setup_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Налаштування торгівлі для будь-якого токена"""
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("0.0001 0.00011 1000000 SOL")
        return ConversationHandler.END
    
    try:
        low_price = float(parts[0])
        high_price = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        uid = update.effective_user.id
        data_store[uid] = {
            "low": low_price,
            "high": high_price,
            "amount": amount,
            "symbol": symbol
        }
        
        await update.message.reply_text(
            f"✅ {symbol} НАЛАШТОВАНО!\n\n"
            f"🟢 Низька ціна: ${low_price}\n"
            f"🔴 Висока ціна: ${high_price}\n"
            f"💰 Кількість: {amount}\n\n"
            f"📊 /test {symbol}\n"
            f"🚀 /monitor 5"
        )
        return ConversationHandler.END
        
    except:
        await update.message.reply_text("0.0001 0.00011 1000000 SOL")
        return ConversationHandler.END

async def start_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск моніторингу"""
    uid = update.effective_user.id
    
    if uid not in data_store:
        await update.message.reply_text("Спочатку: 0.0001 0.00011 1000000 SOL")
        return
    
    try:
        minutes = int(context.args[0]) if context.args else 5
        data = data_store[uid].copy()
        data["interval"] = minutes * 60
        
        if uid in tasks_store:
            tasks_store[uid].cancel()
        
        app = context.application
        task = asyncio.create_task(monitor_prices(uid, app))
        tasks_store[uid] = task
        
        await update.message.reply_text(
            f"🚀 МОНІТОРИНГ {data['symbol']}\n"
            f"⏰ Кожні {minutes} хв\n"
            f"/status /stop"
        )
    except:
        await update.message.reply_text("/monitor 5")

async def monitor_prices(uid, app):
    """Моніторинг цін"""
    data = data_store[uid]
    while uid in tasks_store:
        try:
            prices = get_token_price(data["symbol"])
            
            if len(prices) >= 2:
                min_price = min(prices.values())
                max_price = max(prices.values())
                min_exchange = min(prices, key=prices.get)
                max_exchange = max(prices, key=prices.get)
                
                spread_pct = (max_price - min_price) / min_price * 100
                pnl = data["amount"] * (max_price - min_price)
                
                text = f"📊 {data['symbol']} LIVE\n\n"
                for ex, p in prices.items():
                    text += f"{ex:<10}: ${p:.6f}\n"
                
                text += f"\n🎯 СПРЕД:\n"
                text += f"🟢 {min_exchange}: ${min_price:.6f}\n"
                text += f"🔴 {max_exchange}: ${max_price:.6f}\n"
                text += f"📈 {spread_pct:.2f}% | 💵 ${pnl:.2f}"
                
                await app.bot.send_message(uid, text)
            
            await asyncio.sleep(data["interval"])
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(60)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого налаштовано")
        return
    
    data = data_store[uid]
    prices = get_token_price(data["symbol"])
    
    text = f"📋 {data['symbol']} STATUS\n\n"
    for ex, p in prices.items():
        text += f"{ex:<10}: ${p:.6f}\n"
    
    await update.message.reply_text(text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        tasks_store.pop(uid, None)
        await update.message.reply_text("🛑 ЗУПИНЕНО")
    else:
        await update.message.reply_text("Не запущено")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder
