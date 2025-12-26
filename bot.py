import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

data_store = {}
tasks_store = {}

def get_token_prices(symbol):
    """CoinGecko tickers - всі біржі"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/token_price/{symbol.lower()}"
        r = requests.get(url, params={"vs_currencies": "usd"}, timeout=10)
        data = r.json()
        return data
    except:
        return {}

def get_direct_prices(symbol):
    """Прямі біржі"""
    prices = {}
    symbol_usdt = f"{symbol.upper()}USDT"
    
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["binance_f"] = float(r.json()["price"])
    except:
        pass
    
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol_usdt}", timeout=3)
        prices["mexc"] = float(r.json()["price"])
    except:
        pass
    
    return prices

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/test btc або /test sol")
        return
    
    symbol = context.args[0].lower()
    
    direct_prices = get_direct_prices(symbol)
    coingecko_price = get_token_prices(symbol)
    
    text = f"🧪 {symbol.upper()}\n\n"
    
    for ex, p in direct_prices.items():
        text += f"{ex}: ${p:.4f}\n"
    
    if coingecko_price:
        cg_price = coingecko_price.get(symbol, {}).get("usd")
        if cg_price:
            text += f"coingecko: ${cg_price:.4f}\n"
    
    if len(direct_prices) >= 2:
        prices_list = list(direct_prices.values())
        min_p = min(prices_list)
        max_p = max(prices_list)
        spread = (max_p - min_p) / min_p * 100
        
        min_ex = min(direct_prices, key=direct_prices.get)
        max_ex = max(direct_prices, key=direct_prices.get)
        
        text += f"\n🎯 Спред {min_ex}-{max_ex}:\n"
        text += f"${min_p:.4f} → ${max_p:.4f}\n"
        text += f"{spread:.2f}%"
    
    await update.message.reply_text(text)

async def setup_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 btc")
        return ConversationHandler.END
    
    try:
        low_price = float(parts[0])
        high_price = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].lower()
        
        uid = update.effective_user.id
        data_store[uid] = {
            "low": low_price,
            "high": high_price,
            "amount": amount,
            "symbol": symbol
        }
        
        await update.message.reply_text(
            f"✅ {symbol.upper()} налаштовано\n"
            f"🟢 Низька: ${low_price}\n"
            f"🔴 Висока: ${high_price}\n"
            f"💰 {amount} шт\n\n"
            f"/test {symbol}\n/monitor 5"
        )
        return ConversationHandler.END
    except:
        await update.message.reply_text("87000 87200 0.1 btc")
        return ConversationHandler.END

async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if uid not in data_store:
        await update.message.reply_text("Налаштуй: 87000 87200 0.1 btc")
        return
    
    try:
        minutes = int(context.args[0]) if context.args else 5
        data = data_store[uid].copy()
        data["interval"] = minutes * 60
        
        if uid in tasks_store:
            tasks_store[uid].cancel()
        
        app = context.application
        task = asyncio.create_task(spread_monitor(uid, app))
        tasks_store[uid] = task
        
        await update.message.reply_text(f"🚀 {data['symbol'].upper()} {minutes}хв\n/status /stop")
    except:
        await update.message.reply_text("/monitor 5")

async def spread_monitor(uid, app):
    data = data_store[uid]
    while uid in tasks_store:
        try:
            direct_prices = get_direct_prices(data["symbol"])
            
            if len(direct_prices) >= 2:
                prices_list = list(direct_prices.values())
                min_p = min(prices_list)
                max_p = max(prices_list)
                
                min_ex = min(direct_prices, key=direct_prices.get)
                max_ex = max(direct_prices, key=direct_prices.get)
                
                pnl = data["amount"] * (max_p - min_p)
                
                text = f"{data['symbol'].upper()} LIVE\n\n"
                for ex, p in direct_prices.items():
                    text += f"{ex}: ${p:.4f}\n"
                
                text += f"\nСпред {min_ex}-{max_ex}\n"
                text += f"${min_p:.4f} → ${max_p:.4f}\n"
                text += f"PnL: ${pnl:.2f}"
                
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
    prices = get_direct_prices(data["symbol"])
    
    text = f"{data['symbol'].upper()} STATUS\n\n"
    for ex, p in prices.items():
        text += f"{ex}: ${p:.4f}\n"
    
    await update.message.reply_text(text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        tasks_store.pop(uid, None)
        await update.message.reply_text("Зупинено")
    else:
        await update.message.reply_text("Не запущено")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder
