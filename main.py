import os
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN', 'arnj43aqr2twnobv1rnvikknvycrpd')
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY', 'u1z429dbeunegfhnkfhza9rimzo1ci')
PUSHOVER_API_URL = 'https://api.pushover.net/1/messages.json'

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚀 Бот OK! /add 0x... /status')

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text('Використання: /add 0x123...')
        return
    address = context.args[0].lower()
    if chat_id not in user_
        user_data[chat_id] = {'wallets': [], 'last_tx_hashes': set()}
    label = ' '.join(context.args[1:]) or 'Wallet'
    user_data[chat_id]['wallets'].append({'address': address, 'label': label})
    await update.message.reply_text(f'✅ Додано: {address} ({label})')

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    wallets = user_data.get(chat_id, {}).get('wallets', [])
    if not wallets:
        await update.message.reply_text('Немає гаманців. /add 0x...')
        return
    text = 'Гаманці:\n'
    for i, w in enumerate(wallets):
        text += f'{i}: {w["address"]} ({w["label"]})\n'
    await update.message.reply_text(text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = user_data.get(chat_id, {})
    count = len(data.get('wallets', []))
    await update.message.reply_text(f'Гаманці: {count}. Моніторинг активний.')

def send_pushover(title, message, tx_url):
    payload = {
        'token': PUSHOVER_TOKEN,
        'user': PUSHOVER_USER_KEY,
        'title': title,
        'message': message + '\nTX: ' + tx_url + '\n/gm',
        'priority': '2',
        'retry': '30',
        'expire': '300',
        'sound': 'siren',
        'html': '1'
    }
    requests.post(PUSHOVER_API_URL, data=payload)
    logger.info('🚨 Pushover надіслано')

def check_sales(chat_id):
    data = user_data.get(chat_id)
    if not data or not data.get('wallets'):
        return
    for wallet in data['wallets']:
        address = wallet['address']
        url = 'https://api.bscscan.com/api'
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'desc',
            'apikey': ETHERSCAN_API_KEY
        }
        try:
            r = requests.get(url, params=params)
            resp = r.json()
            if resp['status'] == '1':
                txs = resp['result'][:5]
                for tx in txs:
                    if (tx['from'].lower() == address.lower() and 
                        tx['hash'] not in data['last_tx_hashes']):
                        data['last_tx_hashes'].add(tx['hash'])
                        tx_url = f'https://bscscan.com/tx/{tx["hash"]}'
                        send_pushover(
                            '🚨 ПРОДАЖ!', 
                            f'{wallet["label"]}: {tx["tokenSymbol"]} {tx["value"]}',
                            tx_url
                        )
        except Exception as e:
            logger.error(f'BSCScan помилка: {e}')

async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_sales(update.effective_chat.id)
    await update.message.reply_text('✅ Перевірено продажі')

async def periodic_check(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in list(user_data.keys()):
        check_sales(chat_id)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('add', add_wallet))
    app.add_handler(CommandHandler('list', list_wallets))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('check', check_now))
    app.job_queue.run_repeating(periodic_check, interval=60, first=10)
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
