import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_coingecko_id(symbol):
    """Знаходить CoinGecko ID"""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/list?include_platform=false", timeout=5)
        coins = r.json()
        symbol_lower = symbol.lower()
        for coin in coins:
            if coin["symbol"] == symbol_lower or coin["id"] == symbol_lower:
                return coin["id"]
    except:
        pass
    return None

def get_token_tickers(token_id):
    """CoinGecko tickers для токена"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token_id}/tickers?page=1"
        r = requests.get(url, timeout=10)
        data = r.json()
        return data.get("tickers", [])
    except:
        return []

@app.command("test")
async def test_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /test btc - ВСІ біржі для токена"""
    if not context.args:
        await update.message.reply_text("Використай: /test btc, /test sol, /test eth")
        return
    
    symbol = context.args[0]
    token_id = get_coingecko_id(symbol)
    
    if not token_id:
        await update.message.reply_text(f"❌ {symbol} не знайдено")
        return
    
    tickers = get_token_tickers(token_id)
    
    if not tickers:
        await update.message.reply_text(f"❌ Дані для {symbol} недоступні")
        return
    
    # Збираємо ціни
    exchange_prices = {}
    for ticker in tickers[:25]:
        ex_name = ticker["market"]["name"]
        price = ticker["converted_last"]["usd"]
        if price and ex_name:
            exchange_prices[ex_name] = price
    
    if len(exchange_prices) < 2:
        await update.message.reply_text("❌ Недостатньо бірж")
        return
    
    # Найкращий спред
    sorted_prices = sorted(exchange_prices.items(), key=lambda x: x[1])
    min_ex, min_price = sorted_prices[0]
    max_ex, max_price = sorted_prices[-1]
    spread_pct = (max_price - min_price) / min_price * 100
    
    text = f"🔥 {symbol.upper()} СПРЕД ({len(exchange_prices)} бірж)\n\n"
    
    text += "🟢 ТОП 10 ДЕШЕВІ (КУПИТИ):\n"
    for i, (ex, p) in enumerate(sorted_prices[:10], 1):
        text += f"{i:2d}. {ex:<12}: ${p:,.6f}\n"
    
    text += f"\n🔴 ТОП СПРЕД:\n"
    text += f"🟢 Купити {min_ex}: ${min_price:,.6f}\n"
    text += f"🔴 Продати {max_ex}: ${max_price:,.6f}\n"
    text += f"📊 Спред: {spread_pct:.3f}%\n\n"
    text += f"💎 Налаштувати моніторинг?\n87000 87200 0.1 {symbol}"
    
    await update.message.reply_text(text)

async def setup_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Налаштування торгівлі"""
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    
    try:
        entry_low = float(parts[0])
        entry_high
