import os
import asyncio
import json
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')  
PUSHOVER_USER_KEY = 'nhbdjue'  
PUSHOVER_API_URL = 'https://api.pushover.net/1/messages.json'

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚀 Бот готовий! Команди:\n/add <address> - додати гаманець\n/list - список\n/remove <index> - видалити\n/status - статус\nМоніторинг BSC/ETH продажів → Pushover сирена!')

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text('Вкажи адресу: /add 0x...')
        return
    address = context.args[0].lower()
    if chat_id not in user_
        user_data[chat_id] = {'wallets': [], 'last_tx_hashes': set()}
    user_data[chat_id]['wallets'].append({'address': address, 'label': ' '.join(context.args[1:] or ['Wallet'])})
    await update.message.reply_text(f'✅ Додано {address}')

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    wallets = user_data.get(chat_id, {}).get('wallets', [])
    if not wallets:
        await update.message.reply_text('Пустий список. Додай /add')
        return
    msg = '📋 Гаманці:\n' + '\n'.join([f"{i}: {w['address']} ({w['label']})" for i, w in enumerate(wallets)])
    await update.message.reply_text(msg)

async def remove_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text('Вкажи індекс: /remove 0')
        return
    try:
        idx = int(context.args[0])
        wallets = user_data[chat_id]['wallets']
        del wallets[idx]
        await update.message.reply_text('🗑 Видалено')
    except:
        await update.message.reply_text('Помилка індексу')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = user_data.get(chat_id, {})
    count = len(data.get('wallets', []))
    await update.message.reply_text(f'✅ {count} гаманців. Pushover: {PUSHOVER_USER_KEY[:8]}... Моніторинг запущено.')

def send_pushover(title, message, tx_url):
    data = {
        'token': 'a3LSK9RR5K4J5QPE4PEQ',  
        'user': PUSHOVER_USER_KEY,
        'title': title,
        'message': f"{message}\nTX: {tx_url}\n/gm",
        'priority': '2',  
        'retry': '30',
        'expire': '300',
        'sound': 'siren',
        'html': '1'
    }
    requests.post(PUSHOVER_API_URL, data=data)
    logger.info('🚨 Pushover sent')

def check_sales(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['wallets']:
        return
    for wallet in data['wallets']:
        address = wallet['address']
        url = f"https://api.bscscan.com/api?module=account&action=tokentx&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_API_KEY}"
        resp = requests.get(url).json()
        if resp['status'] != '1':
            continue
        txs = resp['result'][:5]  
        new_hashes = set()
        for tx in txs:
            if tx['from'].lower() == address.lower() and tx['hash'] not in data['last_tx_hashes']:
                new_hashes.add(tx['hash'])
                tx_url = f"https://bscscan.com/tx/{tx['hash']}"
                send_pushover('🚨 ПРОДАЖ!', f"{wallet['label']} продав {tx['value']} {tx['tokenSymbol']}", tx_url)
        data['last_tx_hashes'].update(new_hashes)

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    check_sales(chat_id)
    await update.message.reply_text('🔍 Перевірено. Налаштуй /add')

async def periodic_monitor(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in list(user_data.keys()):
        check_sales(chat_id)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('add', add_wallet))
    app.add_handler(CommandHandler('list', list_wallets))
    app.add_handler(CommandHandler('remove', remove_wallet))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('monitor', monitor))
    app.job_queue.run_repeating(periodic_monitor, interval=60)  
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
