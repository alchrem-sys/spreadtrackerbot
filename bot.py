import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

INTERVAL = 0

data_store = {}
tasks_store = {}

def get_coingecko_prices(symbol):
    """CoinGecko - ціни з 100+ бірж одразу!"""
    try:
        # CoinGecko API - безкоштовний, 100+ бірж
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=5)
        data = r.json()
        
        if symbol.lower() in 
            return {"COINGECKO": data[symbol.lower()]["usd"]}
    except:
        pass
    
    return {}

def get_binance_futures(symbol):
    """Binance Futures (стабільний)"""
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol.upper()}USDT", timeout=3)
        return {"BINANCE_FUTURES": float(r.json()["price"])}
    except:
        return {}

def get_mexc_spot(symbol):
    """MEXC Spot (стабільний)"""
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}USDT", timeout=3)
        return {"MEXC": float(r.json()["price"])}
    except:
        return {}

def get_all_prices(symbol):
    """Агрегує всі джерела"""
    prices = {}
    
    # CoinGecko (основний агрегатор)
    prices.update(get_coingecko_prices(symbol))
    
    # Binance Futures
    prices.update(get_binance_futures(symbol))
    
    # MEXC Spot
    prices.update(get_mexc_spot(symbol))
    
    return prices

async def handle_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return ConversationHandler.END
    
    try:
        entry1 = float(parts[0])
        entry2 = float(parts[1])
        amount = float(parts[2])
        symbol = parts[3].upper()
        
        # Отримуємо ціни з усіх джерел
        prices = get_all_prices(symbol)
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if len(valid_prices) < 2:
            await update.message.reply_text(f"❌ {symbol} мало даних. Спробуй BTC/ETH")
            return ConversationHandler.END
        
        # Найкращий спред
        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        min_ex = next(k for k, v in valid_prices.items() if v == min_price)
        max_ex = next(k for k, v in valid_prices.items() if v == max_price)
        
        spread_pct = (max_price - min_price) / min_price * 100
        pnl = amount * (max_price - min_price)
        
        # Формуємо повідомлення
        text = f"🔥 {symbol} СПРЕД ТРЕЙД\n\n"
        text += f"📈 Вхід: ${entry1:,.0f} → ${entry2:,.0f}\n"
        text += f"💰 Кількість: {amount}\n\n"
        
        text += "💹 ПОТОЧНІ ЦІНИ:\n"
        for ex, price in prices.items():
            status = f"${price:,.0f}" if price else "❌"
            text += f"{ex:<15}: {status}\n"
        
        text += f"\n🎯 НАЙКРАЩА ПАРА:\n"
        text += f"🟢 Купити {min_ex:<15}: ${min_price:,.0f}\n"
        text += f"🔴 Продати {max_ex:<15}: ${max_price:,.0f}\n"
        text += f"📊 Спред: {spread_pct:.2f}%\n"
        text += f"💵 PnL зараз: ${pnl:,.2f}\n\n"
        text += "⏰ Моніторинг кожні (хв):"
        
        context.user_data.update({
            "entry1": entry1, "entry2": entry2, 
            "amount": amount, "symbol": symbol
        })
        
        await update.message.reply_text(text)
        return INTERVAL
        
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}\nПриклад: 87000 87200 0.1 BTC")
        return ConversationHandler.END

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text)
        if minutes < 1 or minutes > 60:
            await update.message.reply_text("1-60 хвилин!")
            return INTERVAL
            
        uid = update.effective_user.id
        data = context.user_data.copy()
        data["interval"] = minutes * 60
        
        data_store[uid] = data
        
        # Зупиняємо стару задачу
        if uid in tasks_store:
            tasks_store[uid].cancel()
        
        app = context.application
        task = asyncio.create_task(monitor_spread(uid, app))
        tasks_store[uid] = task
        
        await update.message.reply_text(
            f"🚀 СПРЕД МОНИТОРИНГ ЗАПУЩЕНО!\n\n"
            f"🪙 {data['symbol']}\n"
            f"⏰ Кожні {minutes} хв\n\n"
            f"📱 /status - поточний статус\n"
            f"🛑 /stop - зупинити"
        )
        return ConversationHandler.END
        
    except:
        await update.message.reply_text("Введи число 1-60")
        return INTERVAL

async def monitor_spread(uid, app):
    """Моніторинг спреду між усіма біржами"""
    data = data_store.get(uid)
    if not 
        return
        
    while uid in tasks_store:
        try:
            prices = get_all_prices(data["symbol"])
            valid_prices = {k: v for k, v in prices.items() if v is not None}
            
            if len(valid_prices) >= 2:
                min_price = min(valid_prices.values())
                max_price = max(valid_prices.values())
                min_exchange = next(k for k, v in valid_prices.items() if v == min_price)
                max_exchange = next(k for k, v in valid_prices.items() if v == max_price)
                
                current_pnl = data["amount"] * (max_price - min_price)
                
                # Сортуємо біржі за ціною
                sorted_exchanges = sorted(valid_prices.items(), key=lambda x: x[1])
                
                text = f"📊 {data['symbol']} СПРЕД LIVE\n\n"
                text += "ЦІНИ:\n"
                for ex, price in sorted_exchanges:
                    text += f"{ex:<15}: ${price:,.2f}\n"
                
                text += f"\n🎯 НАЙКРАЩИЙ СПРЕД:\n"
                text += f"🟢 Купити {min_exchange}: ${min_price:,.2f}\n"
                text += f"🔴 Продати {max_exchange}: ${max_price:,.2f}\n"
                text += f"📈 Спред: {((max_price-min_price)/min_price*100):.2f}%\n"
                text += f"💵 PnL: ${current_pnl:,.2f}"
                
                await app.bot.send_message(uid, text)
            else:
                await app.bot.send_message(uid, f"❌ {data['symbol']} мало даних")
            
            await asyncio.sleep(data["interval"])
            
        except asyncio.CancelledError:
            break
        except:
            await asyncio.sleep(60)

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in tasks_store:
        tasks_store[uid].cancel()
        data_store.pop(uid, None)
        await update.message.reply_text("🛑 Моніторинг зупинено!")
    else:
        await update.message.reply_text("Моніторинг не запущено")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in data_store:
        await update.message.reply_text("Нічого не моніториться\n87000 87200 0.1 BTC")
        return
    
    data = data_store[uid]
    prices = get_all_prices(data["symbol"])
    valid_prices = {k: v for k, v in prices.items() if v is not None}
    
    text = f"📋 {data['symbol']} STATUS\n\n"
    for ex, price in prices.items():
        status = f"${price:,.2f}" if price else "❌"
        text += f"{ex:<15}: {status}\n"
    
    if len(valid_prices) >= 2:
        min_p = min(valid_prices.values())
        max_p = max(valid_prices.values())
        pnl = data["amount"] * (max_p - min_p)
        text += f"\n💵 Поточний PnL: ${pnl:,.2f}"
    
    await update.message.reply_text(text)

async def test_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестує всі біржі"""
    symbol = (context.args[0] if context.args else "BTC").upper()
    prices = get_all_prices(symbol)
    
    text = f"🧪 ТЕСТ {symbol}:\n\n"
    for ex, price in prices.items():
        status = f"${price:,.2f}" if price else "❌"
        text += f"{ex:<15}: {status}\n"
    
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
    app.add_handler(CommandHandler("test", test_prices))
    app.add_handler(CommandHandler("stop", stop_monitor))
    app.add_handler(CommandHandler("status", show_status))
    
    print("🚀 Спред Арбітраж Бот - CoinGecko + біржі!")
    app.run_polling(drop_pending_updates=True)
