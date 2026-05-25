import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Siz Iymona Baby & Kids Store uchun onlayn yordamchisiz.
Do'kon Telegram orqali ishlaydi: @iymona_baby_and_kids_store_bot
Qoidalar:
- Faqat o'zbek tilida javob bering
- Qisqa, samimiy va professional bo'ling (2-4 gap)
- Bolalar mahsulotlari: kiyim, o'yinchoq, parvarish vositalari, aksessuarlar
- Narx yoki aniq mahsulot so'ralganda @iymona_baby_and_kids_store_bot ga yo'naltiring
- Har doim iliq munosabat ko'rsating emoji ishlatishingiz mumkin"""

chat_sessions = {}

def get_chat(user_id):
    if user_id not in chat_sessions:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
        chat_sessions[user_id] = model.start_chat(history=[])
    return chat_sessions[user_id]

async def ask_gemini(user_id, text):
    try:
        loop = asyncio.get_event_loop()
        chat = get_chat(user_id)
        response = await loop.run_in_executor(None, chat.send_message, text)
        return response.text
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return "Uzr, hozir texnik muammo bor. Iltimos, qayta yozing 🙏"

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "do'stim"
    await update.message.reply_text(f"Assalomu alaykum, {name}! 👶🌸\nIymona Baby & Kids Store ga xush kelibsiz!\nSavol bo'lsa so'rashingiz mumkin 😊")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛍 Mahsulotlar, buyurtma, yetkazib berish haqida so'rang!\n📦 Buyurtma: @iymona_baby_and_kids_store_bot")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_sessions.pop(update.effective_user.id, None)
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
        if not text:
            await message.reply_text("Savolingizni yozing 😊")
            return
    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
    reply = await ask_gemini(user_id, text)
    await message.reply_text(reply)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

async def main():
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.initialize()
    await app.start()
    await app. updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
