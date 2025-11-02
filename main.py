# main.py
import os
import logging
import re
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import openai  # replaced Gemini with OpenAI

# logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# env & config
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
SYSTEM_PROMPT_PATH = "prompts/system_prompt.txt"
CREATOR_NAME = "OKAFOR EMMANUEL IKE"
CREATOR_WHATSAPP = "https://wa.link/i7s2lh"

if not TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Missing TELEGRAM_TOKEN or OPENAI_API_KEY in environment variables.")

# load system prompt (teaching personality)
with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()

# mongo (optional)
if MONGO_URI:
    client = MongoClient(MONGO_URI)
    db = client["unizik_ai"]
else:
    db = None

# configure OpenAI
openai.api_key = OPENAI_API_KEY
MODEL = "gpt-4-turbo"

# helper: simple rule-based educational classifier
EDU_KEYWORDS = {
    "define", "definition", "explain", "what", "why", "how", "solve", "calculate",
    "theorem", "proof", "example", "syllabus", "lecture", "course", "exam", "past question",
    "assignment", "lecture notes", "tutorial", "lab", "practical", "essay", "reading",
    "unizik", "nnamdi azikiwe", "nnamdi azikiwe university", "faculty", "department",
    "semester", "result", "timetable"
}

def is_educational(text: str) -> bool:
    t = text.lower()
    if "unizik" in t or "nnamdi azikiwe" in t:
        return True
    if re.search(r"^\s*(what|why|how|explain|define|show|compare|calculate)\b", t):
        return True
    for kw in EDU_KEYWORDS:
        if kw in t:
            return True
    return False

def is_creator_query(text: str) -> bool:
    t = text.lower()
    return any(phrase in t for phrase in ("who created you", "who made you", "who developed you", "who is your creator", "your creator"))

def is_creator_info_query(text: str) -> bool:
    t = text.lower()
    return any(phrase in t for phrase in ("creator info", "owner info", "contact the creator", "contact info", "who is okafor", "how to contact okafor", "my info"))

# call GPT-4-Turbo for a deep answer
def ask_gpt(prompt: str, max_output_tokens: int = 800) -> str:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=max_output_tokens,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Sorry — I couldn't reach the AI service right now."

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello — I am the UNIZIK Academic Assistant. Ask me anything academic or UNIZIK-related; I respond with detailed, lecturer-style explanations."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    if is_creator_query(text):
        await update.message.reply_text(f"I was created by {CREATOR_NAME}.")
        return
    if is_creator_info_query(text):
        await update.message.reply_text(f"Contact the creator: {CREATOR_NAME}\nWhatsApp: {CREATOR_WHATSAPP}")
        return

    if not is_educational(text):
        await update.message.reply_text(
            "I can only help with educational questions or UNIZIK-related academic topics. Please ask a question about a course, concept, syllabus, exam, or UNIZIK-specific info."
        )
        return

    try:
        answer = ask_gpt(text)
    except Exception as e:
        logging.exception("GPT error:")
        await update.message.reply_text("Sorry — I couldn't reach the AI service right now.")
        return

    if len(answer) > 4000:
        answer = answer[:3990] + "\n\n[answer truncated]"
    await update.message.reply_text(answer)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
