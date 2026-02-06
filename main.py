import os
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------------------
verbs = [
    ["beginnen", "begann", "begonnen", "haben"],
    ["bitten", "bat", "gebeten", "haben"],
    ["bleiben", "blieb", "geblieben", "sein"],
    ["essen", "aß", "gegessen", "haben"],
    ["fahren", "fuhr", "gefahren", "sein/haben"],
    ["fallen", "fiel", "gefallen", "sein"],
    ["finden", "fand", "gefunden", "haben"],
    ["gehen", "ging", "gegangen", "sein"],
    ["haben", "hatte", "gehabt", "haben"],
    ["einladen", "lud ein", "eingeladen", "haben"],
    ["leihen", "lieh", "geliehen", "haben"],
    ["rufen", "rief", "gerufen", "haben"],
    ["schreiben", "schrieb", "geschrieben", "haben"],
    ["sprechen", "sprach", "gesprochen", "haben"],
    ["sehen", "sah", "gesehen", "haben"],
    ["springen", "sprang", "gesprungen", "sein"],
    ["sein", "war", "gewesen", "sein"],
    ["stehen", "stand", "gestanden", "haben"],
    ["steigen", "stieg", "gestiegen", "sein"],
    ["trinken", "trank", "getrunken", "haben"],
    ["werden", "wurde", "geworden", "sein"],
    ["wissen", "wusste", "gewusst", "haben"],
    ["ziehen", "zog", "gezogen", "sein/haben"]
]

# ----------------------------

user_data = {}

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("ERROR: BOT_TOKEN missing!")
    exit(1)


def new_round(user_id):
    """Створюємо нове random коло слів"""
    shuffled = verbs[:]
    random.shuffle(shuffled)
    user_data[user_id]["round"] = shuffled
    user_data[user_id]["index"] = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"repeat": 0}

    new_round(user_id)

    await update.message.reply_text(
        "🚀 Починаємо тренування!\n"
        "Формат: Präteritum — Partizip II — допоміжне\n"
        "Якщо мисклік → напиши skip."
    )

    await ask_verb(update, context)


async def ask_verb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # якщо всі слова пройшли → новий random круг
    if user_data[user_id]["index"] >= len(user_data[user_id]["round"]):
        new_round(user_id)
        await update.message.reply_text("🔄 Нове коло слів!")

    verb = user_data[user_id]["round"][user_data[user_id]["index"]][0]
    await update.message.reply_text(f"👉 Дієслово: {verb}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("Напиши /start")
        return

    current = user_data[user_id]["round"][user_data[user_id]["index"]]
    correct = current[1:]

    answer = update.message.text.lower().replace(" ", "").strip()
    correct_answer = "".join(correct).lower()

    # skip повторів
    if answer == "skip" and user_data[user_id]["repeat"] > 0:
        user_data[user_id]["repeat"] = 0
        user_data[user_id]["index"] += 1
        await update.message.reply_text("⏭ Пропущено.")
        await ask_verb(update, context)
        return

    if answer == correct_answer:
        if user_data[user_id]["repeat"] > 0:
            user_data[user_id]["repeat"] -= 1
            await update.message.reply_text(
                f"✅ Добре. Ще {user_data[user_id]['repeat']} раз."
            )
        else:
            await update.message.reply_text("✅ Правильно!")
            user_data[user_id]["index"] += 1
            await ask_verb(update, context)
    else:
        user_data[user_id]["repeat"] = 5
        await update.message.reply_text(
            "❌ Помилка.\n"
            f"Напиши 5 разів або skip:\n{' — '.join(correct)}"
        )


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running...")
app.run_polling()
