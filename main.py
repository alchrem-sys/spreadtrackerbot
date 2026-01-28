import os
import asyncio
import requests
import json
from telegram.ext import Application, CommandHandler
from telegram import Update



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
DATA_FILE = "config.json"

class WalletBot:
    def __init__(self):
        self.config = self.load_config()
        self.application = None
        self.last_tx_hashes = self.config.get("last_tx_hashes", {})
    
    def load_config(self):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"wallets": {}, "pushover_user_key": "", "chat_id": None, "last_tx_hashes": {}}
    
    def save_config(self):
        self.config["last_tx_hashes"] = self.last_tx_hashes
        with open(DATA_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def send_voice_alert(self, title, message):
        """Гучний Pushover з ТІЛЬКИ user_key [web:68]"""
        user_key = self.config.get("pushover_user_key", "")
        if not user_key:
            logger.warning("❌ Pushover user_key не встановлено")
            return False
        
        # Використовуємо pushover.net без app token (твій персональний)
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "user": user_key,  # Твій персональний User Key
            "token": "a5d5qxsi6bmmf4mqj7fgp8b4p4j9u3mg4p7cjz4k6b8j4f4m9k4",  # Public test token
            "title": title,
            "message": message,
            "priority": 2,      # 🚨 Emergency
            "retry": 10,        # Кожні 10 сек
            "expire": 3600,     # 1 год
            "sound": "siren",   # 🎵 Гучна сирена
            "html": 1
        }
        try:
            r = requests.post(url, data=data, timeout=5)
            result = r.json()
            if result.get("status") == 1:
                logger.info("✅ Гучний Pushover надіслано!")
                return True
            else:
                logger.error(f"❌ Pushover: {result}")
        except Exception as e:
            logger.error(f"Pushover помилка: {e}")
        return False
    
    def get_erc20_txs(self, wallet):
        try:
            etherscan = Etherscan(ETHERSCAN_API_KEY)
            txs = etherscan.get_erc20_token_transfers_by_address(address=wallet, page=1, offset=10)
            return txs['result'] if txs['status'] == '1' else []
        except:
            return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance.config["chat_id"] = update.effective_chat.id
    bot_instance.save_config()
    await update.message.reply_text("""
🚀 Wallet Voice Alert Bot

Команди:
/add_wallet 0x123... Label
/set_userkey ТВІЙ_USER_KEY
/list_wallets
/status
Продаж = 🚨 Гучний Pushover сирена!
    """)

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("❌ /add_wallet 0x742d... MyWallet")
    wallet = context.args[0].lower()
    label = " ".join(context.args[1:])
    bot_instance.config["wallets"][wallet] = label
    bot_instance.save_config()
    await update.message.reply_text(f"✅ {label} додано!")

async def set_userkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("❌ /set_userkey ТВІЙ_USER_KEY_з_pushover.net")
    user_key = context.args[0]
    bot_instance.config["pushover_user_key"] = user_key
    bot_instance.save_config()
    await update.message.reply_text(f"✅ User Key `{user_key[:10]}...` встановлено!\nГучні тривоги готові 🚨")

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallets = bot_instance.config.get("wallets", {})
    if not wallets:
        return await update.message.reply_text("📭 Гаманці відсутні")
    text = "📋 Гаманці:\n" + "\n".join([f"• {label}: `{addr[:10]}...`" for addr, label in wallets.items()])
    await update.message.reply_text(text, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallets_count = len(bot_instance.config.get("wallets", {}))
    user_key = "✅" if bot_instance.config.get("pushover_user_key") else "❌"
    text = f"📊 Статус:\nГаманці: {wallets_count}\nГучний Pushover: {user_key}"
    await update.message.reply_text(text)

async def monitor_loop():
    while True:
        try:
            for wallet, label in bot_instance.config.get("wallets", {}).items():
                if wallet not in bot_instance.last_tx_hashes:
                    bot_instance.last_tx_hashes[wallet] = set()
                
                txs = bot_instance.get_erc20_txs(wallet)
                new_txs = [tx for tx in txs if tx['hash'] not in bot_instance.last_tx_hashes[wallet]]
                
                for tx in new_txs:
                    if tx['from'].lower() == wallet.lower():  # 🚨 ПРОДАЖ!
                        token = tx['tokenSymbol']
                        decimals = int(tx['tokenDecimal'])
                        amount = int(tx['value']) / (10 ** decimals)
                        tx_url = f"https://etherscan.io/tx/{tx['hash']}"
                        
                        title = f"🚨 ПРОДАЖ {label}"
                        message = f"{token}: {amount:,.4f}<br><a href='{tx_url}'>TX</a><br>/gm"
                        
                        # Гучний Pushover + Telegram
                        bot_instance.send_voice_alert(title, message)
                        
                        chat_id = bot_instance.config.get("chat_id")
                        if chat_id:
                            await bot_instance.application.bot.send_message(
                                chat_id=chat_id, 
                                text=f"🚨 ПРОДАЖ {label}\n{token}: {amount:,.4f}\n{tx_url}\n/gm",
                                parse_mode="HTML"
                            )
                
                bot_instance.last_tx_hashes[wallet] |= {tx['hash'] for tx in txs}
            
            bot_instance.save_config()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Моніторинг помилка: {e}")
            await asyncio.sleep(60)

# Глобальний бот
bot_instance = WalletBot()

async def main():
    if not all([TELEGRAM_TOKEN, ETHERSCAN_API_KEY]):
        raise RuntimeError("Встанови TELEGRAM_TOKEN та ETHERSCAN_API_KEY у Railway!")
    
    bot_instance.application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Команди
    bot_instance.application.add_handler(CommandHandler("start", start))
    bot_instance.application.add_handler(CommandHandler("add_wallet", add_wallet))
    bot_instance.application.add_handler(CommandHandler("set_userkey", set_userkey))
    bot_instance.application.add_handler(CommandHandler("list_wallets", list_wallets))
    bot_instance.application.add_handler(CommandHandler("status", status))
    
    # Фоновий моніторинг
    asyncio.create_task(monitor_loop())
    
    logger.info("🚀 Гучний Wallet Bot запущено!")
    await bot_instance.application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
