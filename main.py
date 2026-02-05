import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------------------
verbs = [
    ["steigen", "stieg", "gestiegen", "sein"],
    ["werden", "wurde", "geworden", "sein"],
    ["beginnen", "begann", "begonnen", "haben"],
    ["wissen", "wusste", "gewusst", "haben"],
    ["essen", "ass", "gegessen", "haben"],
    ["fahren", "fuhr", "gefahren", "sein"],
    ["springen", "sprang", "gesprungen", "sein"],
    ["rufen", "rief", "gerufen", "haben"],
    ["leihen", "lieh", "geliehen", "haben"],
    ["bleiben", "blieb", "geblieben", "sein"]
]
# ----------------------------

user_data = {}

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("ERROR: Не знайдено BOT_TOKEN в environment variables!")
    exit(1)

# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"index": 0, "repeat": 0}
    await update.message.reply_text(
        "Привіт! Почнемо тренування.\n"
        "Відповідай у форматі: Präteritum Partizip II допоміжне\n"
        "Якщо випадково натиснув не ту клавішу, напиши `skip`, щоб пропустити повтори."
    )
    await ask_verb(update, context)

async def ask_verb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    index = user_data[user_id]["index"]
    verb = verbs[index % len(verbs)][0]
    await update.message.reply_text(f"Дієслово: {verb}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("Напиши /start, щоб почати тренування.")
        return

    index = user_data[user_id]["index"]
    repeat = user_data[user_id]["repeat"]
    correct = verbs[index % len(verbs)][1:]  # Präteritum, Partizip II, допоміжне

    answer = update.message.text.strip().lower().replace(" ", "")
    correct_answer = "".join(correct).lower()

    # Якщо користувач пише "skip", пропускаємо повтори
    if answer == "skip" and repeat > 0:
        user_data[user_id]["repeat"] = 0
        await update.message.reply_text("🔹 Пропущено повтори, рухаємося далі.")
        user_data[user_id]["index"] += 1
        await ask_verb(update, context)
        return

    # Перевірка правильної відповіді
    if answer == correct_answer:
        if repeat > 0:
            user_data[user_id]["repeat"] -= 1
            await update.message.reply_text(
                f"✅ Правильно! Повторіть ще {user_data[user_id]['repeat']} разів."
            )
        else:
            await update.message.reply_text("✅ Абсолютно правильно!")
            user_data[user_id]["index"] += 1
            user_data[user_id]["repeat"] = 0
            await ask_verb(update, context)
    else:
        user_data[user_id]["repeat"] = 5
        await update.message.reply_text(
            f"❌ Неправильно. Тепер напиши правильну форму **5 разів** або введи `skip`:\n"
            f"{' — '.join(correct)}"
        )

# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущено...")
app.run_polling()
