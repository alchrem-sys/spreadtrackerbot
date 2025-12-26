import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}
coingecko_cache = {}

def get_coingecko_id(symbol):
    """Знаходить CoinGecko ID для будь-якого токена"""
    symbol_lower = symbol.lower()
    if symbol_lower in coingecko_cache:
        return coingecko_cache[symbol_lower]
    
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=5)
        coins = r.json()
        for coin in coins:
            if coin["symbol"] == symbol_lower or coin["id"] == symbol_lower:
                coingecko_cache[symbol_lower] = coin["id"]
                return coin["id"]
    except:
        pass
    return None

def get_token_exchanges(token_id):
    """Отримує ціни з топ бірж CoinGecko"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token_id}/tickers?page=1"
        r = requests.get(url, timeout=10)
        data = r.json()
        return data.get("tickers", [])
    except:
        return []

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /test btc - показує ВСІ біржі + найкращий спред"""
    if not context.args:
        await update.message.reply_text("Використай: /test btc або /test sol")
        return
    
    symbol = context.args[0]
    token_id = get_coingecko_id(symbol)
    
    if not token_id:
        await update.message.reply_text(f"❌ Токен {symbol} не знайдено. Спробуй btc, eth, sol")
        return
    
    tickers = get_token_exchanges(token_id)
    
    if not tickers:
        await update.message.reply_text(f"❌ Немає даних для {symbol}")
        return
    
    # Збираємо ціни з бірж
    exchange_prices = {}
    for ticker in tickers[:30]:  # Топ 30 бірж
        ex_name = ticker["market"]["name"]
        price = ticker["converted_last"]["usd"]
        if price and ex_name:
            exchange_prices[ex_name] = price
    
    if len(exchange_prices) < 2:
        await update.message.reply_text("❌ Мало бірж з цінами")
        return
    
    # Найкращий спред
    sorted_exchanges = sorted(exchange_prices.items(), key=lambda x: x[1])
    min_ex, min_price = sorted_exchanges[0]
    max_ex, max_price = sorted_exchanges[-1]
    spread_pct = (max_price - min_price) / min_price * 100
    
    text = f"🔥 {symbol.upper()} - ТОП СПРЕД\n\n"
    
    # Топ 10 найдешевші
    text += "🟢 НАЙДешевші (КУПИТИ):\n"
    for i, (ex, p) in enumerate(sorted_exchanges[:10], 1):
        text += f"{i}. {ex:<12}: ${p:,.6f}\n"
    
    text += f"\n🔴 НАЙДорожчі (ПРОДАТИ):\n"
    top_expensive = sorted_exchanges[-10:]
    for i, (ex, p) in enumerate(reversed(top_expensive), 1):
        text += f"{i}. {ex:<12}: ${p:,.6f}\n"
    
    text += f"\n🎯 НАЙКРАЩИЙ СПРЕД:\n"
    text += f"🟢 Купити {min_ex}: ${min_price:,.6f}\n"
    text += f"🔴 Продати {max_ex}: ${max_price:,.6f}\n"
    text += f"📊 Спред: {spread_pct:.3f}%\n\n"
    text += f"💎 Запустити моніторинг?\n/start {symbol}"
    
    await update.message.reply_text(text)

async def setup_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Налаштування торгівлі"""
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    
    try:
        entry_low = float(parts[0])
        entry_high = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].lower()
        
        uid = update.effective_user.id
        data_store[uid] = {
            "entry_low": entry_low,
            "entry_high": entry_high,
            "amount": amount,
            "symbol": symbol
        }
        
        await update.message.reply_text(
            f"✅ {symbol.upper()} НАЛАШТОВАНО!\n\n"
            f"🟢 Вхід низька: ${entry_low}\n"
            f"🔴 Вхід висока: ${entry_high}\n"
            f"💰 Кількість: {amount}\n\n"
            f"📊 /test {symbol} - перевірити спред\n"
            f"⏰ /monitor 5 - моніторинг 5 хв"
        )
        return ConversationHandler.END
        
    except:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END

async def start_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск моніторингу"""
    uid = update.effective_user.id
    
    if uid not in data_store:
        await update.message.reply_text("Спочатку налаштуй торгівлю:\n87000 87200 0.1 BTC")
        return
    
    try:
        minutes = int(context.args[0]) if context.args else 5
        data = data_store[uid].copy()
        data["interval"] = minutes * 60
        
        if uid in tasks_store:
            tasks_store[uid].cancel()
        
        app = context.application
        task = asyncio.create_task(monitor_loop(uid, app))
        tasks_store[uid] = task
        
        await update.message.reply_text(
            f"🚀 МОНІТОРИНГ {data['symbol'].upper()}\n"
            f"⏰ Кожні {minutes} хв\n"
            f"📱 /status /stop"
        )
    except:
        await update.message.reply_text("Використай: /monitor 5")

async def monitor_loop(uid, app):
    """Головний цикл моніторингу"""
    data = data_store[uid]
    while uid in tasks_store:
        try:
            token_id = get_coingecko_id(data["symbol"])
            if token_id:
                tickers = get_token_exchanges(token_id)
                exchange_prices = {}
                
                for ticker in tickers[:20]:
                    ex_name = ticker["market"]["name"]
                    price = ticker["converted_last"]["usd"]
                    if price and ex_name:
                        exchange_prices[ex_name] = price
                
                if len(exchange_prices) >= 2:
                    sorted_prices = sorted(exchange_prices.items(), key=lambda x: x[1])
                    min_ex, min_p = sorted_prices[0]
                    max_ex, max_p = sorted_prices[-1]
                    
                    spread = (max_p - min_p) / min_p * 100
                    pnl = data["amount"] * (max_p - min_p)
                    
                    text = f"📊 {data['symbol'].upper()} LIVE\n\n"
                    text += "ТОП 5 СПРЕД:\n"
                    for ex, p in sorted_prices[:5]:
                        text += f"{ex:<12}: ${p:,.6f}\n"
                    
                    text += f"\n🎯 АКТУАЛЬНИЙ СПРЕД:\n"
                    text += f"🟢 {min_ex}: ${min_p:,.6f}\n"
                    text += f"🔴 {max_ex}: ${max_p:,.6f}\n"
                    text += f"📈 {spread:.3f}% | 💵 ${pnl:,.2f}"
                    
                    await app.bot.send_message(uid, text)
            
            await asyncio.sleep(data["interval"])
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(60)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого налаштовано\n87000 87200 0.1 BTC")
        return
    
    data = data_store[uid]
    token_id = get_coingecko_id(data["symbol"])
    
    if token_id:
        tickers = get_token_exchanges(token_id)
        exchange_prices = {}
        
        for ticker in tickers[:15]:
            ex_name = ticker["market"]["name"]
            price = ticker["converted_last"]["usd"]
            if price and ex_name:
                exchange_prices[ex_name] = price
        
        if exchange_prices:
            sorted_prices = sorted(exchange_prices.items(), key=lambda x: x[1])
            min_ex, min_p = sorted_prices[0]
            max_ex, max_p = sorted_prices[-1]
            pnl = data["amount"] * (max_p - min_p)
            
            text = f"📋 {data['symbol'].upper()} STATUS\n\n"
            for ex, p in sorted_prices[:10]:
                text += f"{ex:<12}: ${p:,.6f}\n"
            
            text += f"\nPnL: ${pnl:,.2f}"
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("Ціни недоступні")
    else:
        await update.message.reply_text("Токен не знайдено")

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
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.text & ~filters.command, setup_trade)],
        states={INTERVAL: []},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("monitor", start_monitor))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    
    print("🚀 Спред Бот - ВСІ ТОКЕНИ!")
    app.run_polling(drop_pending_updates=True)
