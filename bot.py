import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Siz Iymona Baby & Kids Store uchun onlayn yordamchisiz.
Telegram: @iymona_baby_and_kids_store_bot
Mahsulotlar: chaqaloqlar aksessuarlari, gel, shampun, krem, moy
Narxlar: 15000 dan 200000 so'mgacha
Yetkazib berish: faqat Jizzax
To'lov: Click, Payme, Humo, naqd
Faqat o'zbek tilida, 2-4 gap, iliq munosabat."""

async def ask_gemini(text, history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    messages = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}, {"role": "model", "parts": [{"text": "Tushunarli, yordam beraman!"}]}]
    for h in history[-6:]:
        messages.append(h)
    messages.append({"role": "user", "parts": [{"text": text}]})
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json={"contents": messages})
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

chat_history = {}

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "do'stim"
    await update.message.reply_text(f"Assalomu alaykum, {name}! 👶🌸\nIymona Baby & Kids Store ga xush kelibsiz!\nSavol bo'lsa so'rashingiz mumkin 😊")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_history.pop(update.effective_user.id, None)
    await update.message.reply_text("Suhbat tozalandi 😊")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return
    text = message.text.strip()
    user_id = message.from_user.id
    if message.chat.type in ("group", "supergroup"):
        is_mention = BOT_USERNAME and f"@{BOT_USERNAME}" in text
        is_reply = message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot
        if not is_mention and not is_reply:
            return
        text = text.replace(f"@{BOT_USERNAME}", "").strip()
    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
    history = chat_history.get(user_id, [])
    try:
        reply = await ask_gemini(text, history)
        history.append({"role": "user", "parts": [{"text": text}]})
        history.append({"role": "model", "parts": [{"text": reply}]})
        chat_history[user_id] = history[-10:]
        await message.reply_text(reply)
    except Exception as e:
        logger.error(f"Xato: {e}")
        await message.reply_text("Uzr, hozir texnik muammo bor. Iltimos, qayta yozing 🙏")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

async def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
