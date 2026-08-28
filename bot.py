import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from gtts import gTTS
import playsound

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTS:
    def __init__(self):
        self.language = 'ru'
        self.slow = False
        
    def speak(self, text, lang='ru'):
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tts.save(tmp.name)
                playsound.playsound(tmp.name)
                os.unlink(tmp.name)
            return True
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False


tts = TTS()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Say", callback_data="speak")],
        [InlineKeyboardButton("Language", callback_data="language")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"TTS Bot\n\n"
        f"Send text and I will speak it.\n"
        f"Language: {tts.language}\n\n"
        f"/start - Menu\n"
        f"/help - Help\n"
        f"/speak [text] - Speak\n"
        f"/lang [ru/en] - Language",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Menu\n"
        "/help - Help\n"
        "/speak [text] - Speak\n"
        "/lang [ru/en] - Language\n\n"
        "Example: /speak Hello"
    )


async def speak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /speak Hello")
        return
        
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text}")
    
    import threading
    def speak_thread():
        tts.speak(text, tts.language)
    threading.Thread(target=speak_thread, daemon=True).start()


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Language: {tts.language}. Use /lang [ru/en]")
        return
        
    lang = context.args[0].lower()
    if lang in ['ru', 'en']:
        tts.language = lang
        await update.message.reply_text(f"Language: {lang}")
    else:
        await update.message.reply_text("Supported: ru, en")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith('/'):
        return
        
    await update.message.reply_text(f"Speaking: {text[:50]}...")
    
    import threading
    def speak_thread():
        tts.speak(text, tts.language)
    threading.Thread(target=speak_thread, daemon=True).start()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "speak":
        await query.edit_message_text("Send text and I will speak it.")
    elif query.data == "language":
        keyboard = [
            [InlineKeyboardButton("Russian", callback_data="lang_ru")],
            [InlineKeyboardButton("English", callback_data="lang_en")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Language: {tts.language}", reply_markup=reply_markup)
    elif query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        tts.language = lang
        await query.edit_message_text(f"Language: {lang}")


def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("speak", speak_command))
        application.add_handler(CommandHandler("lang", lang_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("Bot started!")
        print("Bot started!")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
