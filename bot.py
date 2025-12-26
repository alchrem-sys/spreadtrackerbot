import os
import asyncio
import logging
import requests
from typing import Dict, Optional
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    ConversationHandler, 
    filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Endpoints
EXCHANGE_APIS = {
    "mexc": {"url": "https://api.mexc.com/api/v3/ticker/price", "param": "symbol"},
    "binance": {"url": "https://api.binance.com/api/v3/ticker/price", "param": "symbol"},
    "gate": {"url": "https://api.gateio.ws/api/v4/spot/tickers", "param": "currency_pair"},
    "bitget": {"url": "https://api.bitget.com/api/spot/v1/market/ticker", "param": "symbol"},
    "orbit": {"url": "https://api.orbitchain.io/v1/market/ticker", "param": "symbol"}
}

GMGN_URL = "https://gmgn.ai/defi/quotation/v1/tokens"

PRICE1, EXCHANGE1, EXCHANGE2, INTERVAL = range(4)

# Global storage for Railway
user_ Dict[int, Dict] = {}
user_tasks: Dict[int, asyncio.Task] = {}

def get_cex_price(exchange: str, symbol: str) -> Optional[float]:
    """Get price from CEX"""
    config = EXCHANGE_APIS.get(exchange.lower())
    if not config:
        return None
    
    try:
        if exchange.lower() == "gate":
            resp = requests.get(f"{config['url']}?currency_pair={symbol.upper()}_USDT", timeout=5)
            data = resp.json()
            return float(data[0]["last"]) if data else None
        elif exchange.lower() == "bitget":
            resp = requests.get(f"{config['url']}?symbol={symbol.upper()}USDT", timeout=5)
            data = resp.json().get("data", [])
            return float(data[0]["lastPr"]) if data else None
        else:
            resp = requests.get(config['url'], params={config['param']: f"{symbol.upper()}USDT"}, timeout=5)
            data = resp.json()
            return float(data["price"]) if isinstance(data, dict) and "price" in data else None
    except:
        return None

def get_gmgn_price(token_address: str) -> Optional[float]:
    """Get price from GMGN DEX"""
    try:
        resp = requests.get(f"{GMGN_URL}/{token_address}", timeout=10)
        data = resp.json()
        return float(data.get("price", 0)) if data else None
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Спред PnL Бот\n\n"
        "Введи початкові дані:\n"
        "ціна1 ціна2 токени символ\n\n"
        "Приклад:\n"
        "0.54 0.58 1000 sol"
    )
    return PRICE1

async def get_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split()
        if len(parts) < 4:
            await update.message.reply_text("Формат: ціна1 ціна2 токени символ\nПриклад: 0.54 0.58 1000 sol")
            return PRICE1
        
        price1 = float(parts[0])
        price2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].lower()
        
        context.user_data.update({
            "price1": price1, "price2": price2, "amount": amount, 
            "symbol": symbol, "initial_spread_pct": ((price2-price1)/price1)*100
        })
        
        await update.message.reply_text(
            f"✅ Зафіксовано вхід:\n"
            f"📈 Ціна 1: ${price1:.8f}\n"
            f"📉 Ціна 2: ${price2:.8f}\n"
            f"💰 Токенів: {amount:,}\n"
            f"🪙 {symbol.upper()}\n\n"
            f"💹 Початковий спред: {((price2-price1)/price1)*100:.2f}%\n"
            f"💵 Початковий PnL: ${(price2-price1)*amount:.2f}\n\n"
            f"Введи біржу №1 (mexc, binance, gate, bitget, orbit, gmgn:контракт):"
        )
        return EXCHANGE1
    except ValueError:
        await update.message.reply_text("Неправильний формат чисел")
        return PRICE1

async def get_exchange1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["exchange1"] = update.message.text.strip().lower()
    await update.message.reply_text("Введи біржу №2 (mexc, binance, gate, bitget, orbit, gmgn:контракт):")
    return EXCHANGE2

async def get_exchange2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["exchange2"] = update.message.text.strip().lower()
    
    await update.message.reply_text(
        "⏰ Введи інтервал в хвилинах (1-60):\n"
        "Приклад: 5"
    )
    return INTERVAL

async def get_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        interval_min = int(update.message.text.strip())
        if interval_min < 1 or interval_min > 60:
            await update.message.reply_text("Інтервал 1-60 хвилин")
            return INTERVAL
        
        user_id = update.effective_user.id
        data = context.user_data.copy()
        data.update({"interval_min": interval_min})
        
        user_data[user_id] = data
        
        # Stop previous task
        if user_id in user_tasks and not user_tasks[user_id].done():
            user_tasks[user_id].cancel()
        
        # Start new monitoring task
        app = context.application
        task = asyncio.create_task(monitor_spread(user_id, app))
        user_tasks[user_id] = task
        
        await update.message.reply_text(
            f"🚀 Моніторинг запущено!\n\n"
            f"⏰ Оновлення: кожні {interval_min} хв\n"
            f"🪙 {data['symbol'].upper()}\n"
            f"💱 {data['exchange1']} ↔ {data['exchange2']}\n\n"
            f"📱 /status - поточний PnL\n"
            f"🛑 /stop - зупинити"
        )
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Введи число (1-60)")
        return INTERVAL

async def monitor_spread(user_id: int, app):
    """Background monitoring task"""
    data = user_data[user_id]
    interval_sec = data["interval_min"] * 60
    initial_pnl_usd = data["amount"] * (data["price2"] - data["price1"])
    
    while user_id in user_tasks:
        try:
            exchange1 = data["exchange1"]
            exchange2 = data["exchange2"]
            symbol = data["symbol"]
            
            price1 = get_gmgn_price(exchange1.split(":")[1]) if "gmgn" in exchange1 else get_cex_price(exchange1, symbol)
            price2 = get_gmgn_price(exchange2.split(":")[1]) if "gmgn" in exchange2 else get_cex_price(exchange2, symbol)
            
            if price1 and price2:
                current_pnl_usd = data["amount"] * (price2 - price1)
                pnl_change_pct = ((current_pnl_usd - initial_pnl_usd) / initial_pnl_usd) * 100 if initial_pnl_usd != 0 else 0
                current_spread_pct = ((price2 - price1) / price1) * 100
                
                text = (
                    f"📊 {data['symbol'].upper()} PnL\n\n"
                    f"💱 {data['exchange1']}: ${price1:.8f}\n"
                    f"💰 {data['exchange2']}: ${price2:.8f}\n\n"
                    f"📈 Спред: {current_spread_pct:.2f}%\n"
                    f"💵 PnL: ${current_pnl_usd:+.2f} ({pnl_change_pct:+.1f}%)"
                )
                
                await app.bot.send_message(chat_id=user_id, text=text)
            
            await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Monitor error {user_id}: {e}")
            await asyncio.sleep(60)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_tasks and not user_tasks[user_id].done():
        user_tasks[user_id].cancel()
        if user_id in user_
            del user_data[user_id]
        await update.message.reply_text("🛑 Моніторинг зупинено")
    else:
        await update.message.reply_text("Моніторинг не активний")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_
        await update.message.reply_text("Немає активних моніторингів")
        return
    
    data = user_data[user_id]
    exchange1, exchange2, symbol = data["exchange1"], data["exchange2"], data["symbol"]
    
    price1 = get_gmgn_price(exchange1.split(":")[1]) if "gmgn" in exchange1 else get_cex_price(exchange1, symbol)
    price2 = get_gmgn_price(exchange2.split(":")[1]) if "gmgn" in exchange2 else get_cex_price(exchange2, symbol)
    
    if price1 and price2:
        current_pnl_usd = data["amount"] * (price2 - price1)
        initial_pnl_usd = data["amount"] * (data["price2"] - data["price1"])
        pnl_change_pct = ((current_pnl_usd - initial_pnl_usd) / initial_pnl_usd) * 100 if initial_pnl_usd != 0 else 0
        current_spread_pct = ((price2 - price1) / price1) * 100
        
        text = (
            f"📋 Поточний статус\n\n"
            f"🪙 {symbol.upper()}\n"
            f"💱 {exchange1} ↔ {exchange2}\n"
            f"💰 Токенів: {data['amount']:,}\n\n"
            f"💰 Ціни:\n"
            f"  {exchange1}: ${price1:.8f}\n"
            f"  {exchange2}: ${price2:.8f}\n\n"
            f"📈 Спред: {current_spread_pct:.2f}%\n"
            f"💵 PnL: ${current_pnl_usd:+.2f} ({pnl_change_pct:+.1f}%)"
        )
    else:
        text = "Не вдалось отримати ціни"
    
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Скасовано")
    return ConversationHandler.END

def main():
    if not os.getenv("BOT_TOKEN"):
        logger.error("BOT_TOKEN not set!")
        return
    
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PRICE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prices)],
            EXCHANGE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_exchange1)],
            EXCHANGE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_exchange2)],
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    logger.info("🚀 Спред PnL Бот запущено на Railway!")
    app.run_polling()

if __name__ == "__main__":
    main()
