import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

EXCHANGE1, EXCHANGE2, INTERVAL = range(3)

data_store = {}
tasks_store = {}

def get_futures_price(exchange, symbol):
    symbol_usdt = f"{symbol.upper()}USDT"
    
    try:
        if exchange == "binance":
            r = requests.get("https://fapi.binance.com/fapi/v1/ticker/price", params={"symbol": symbol_usdt}, timeout=5)
            return float(r.json()["price"])
    except:
        return None
    return None

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
        
        await update.message.reply_text(
            f"✅ {symbol} | {amount} шт\n"
            f"Вхід: ${price1} → ${price2}\n\n"
            "binance/mexc/bitget/gate/bingx:"
        )
        return EXCHANGE1
    except:
        await update.message.reply_text("87000 87200 0.1 BTC")
        return EXCHANGE1

async def exch1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ex1"] = update.message.text.strip().lower()
    await update.message.reply_text("Біржа2 (binance/mexc/bitget/gate/bingx):")
    return EXCHANGE2

async def exch2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ex2"] = update.message.text.strip().lower()
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
            f"🚀 ЗАПУЩЕНО!\n\n"
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
                text = (
                    f"📊 {data['sym']} LIVE\n\n"
                    f"💱 {data['ex1'].upper()}: ${p1:,.2f}\n"
                    f"💰 {data['ex2'].upper()}: ${p2:,.2f}\n"
                    f"💵 PnL: ${pnl:+,.2f}"
                )
                await app.bot.send_message(uid, text)
            else:
                await app.bot.send_message(uid, f"❌ {data['sym']} немає")
            
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
            f"📋 STATUS\n"
            f"{data['ex1'].upper()}: ${p1:,.2f}\n"
            f"{data['ex2'].upper()}: ${p2:,.2f}\n"
            f"💵 PnL: ${pnl:+,.2f}"
        )
    else:
        await update.message.reply_text("❌ Ціни немає")

async def test_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = (context.args[0] if context.args else "BTC").upper()
    p = get_futures_price("binance", symbol)
    await update.message.reply_text(f"🧪 Binance {symbol}: ${p:,.2f}" if p else f"❌ {symbol} немає")

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
    app.add_handler(CommandHandler("test", test_api))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    
    print("🚀 ПРОСТИЙ Бот!")
    app.run_polling()
