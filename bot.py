import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from gtts import gTTS
import io

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Доступные языки и голоса
LANGUAGES = {
    'ru': {'name': 'Russian', 'tld': 'ru', 'voices': ['ru', 'ru-ua', 'ru-by']},
    'en': {'name': 'English', 'tld': 'com', 'voices': ['en-us', 'en-uk', 'en-au', 'en-in', 'en-ca']},
    'es': {'name': 'Spanish', 'tld': 'es', 'voices': ['es-es', 'es-mx', 'es-ar']},
    'fr': {'name': 'French', 'tld': 'fr', 'voices': ['fr-fr', 'fr-ca']},
    'de': {'name': 'German', 'tld': 'de', 'voices': ['de-de']},
    'it': {'name': 'Italian', 'tld': 'it', 'voices': ['it-it']},
    'pt': {'name': 'Portuguese', 'tld': 'pt', 'voices': ['pt-pt', 'pt-br']},
    'ja': {'name': 'Japanese', 'tld': 'co.jp', 'voices': ['ja']},
    'ko': {'name': 'Korean', 'tld': 'co.kr', 'voices': ['ko']},
    'zh': {'name': 'Chinese', 'tld': 'cn', 'voices': ['zh-cn', 'zh-tw']},
    'ar': {'name': 'Arabic', 'tld': 'sa', 'voices': ['ar']},
    'hi': {'name': 'Hindi', 'tld': 'in', 'voices': ['hi']},
}

# Голоса (tld) с названиями для отображения
VOICE_NAMES = {
    'ru': 'Russian (Male)',
    'ru-ua': 'Russian (Ukraine)',
    'ru-by': 'Russian (Belarus)',
    'en-us': 'English (US)',
    'en-uk': 'English (UK)',
    'en-au': 'English (Australia)',
    'en-in': 'English (India)',
    'en-ca': 'English (Canada)',
    'es-es': 'Spanish (Spain)',
    'es-mx': 'Spanish (Mexico)',
    'es-ar': 'Spanish (Argentina)',
    'fr-fr': 'French (France)',
    'fr-ca': 'French (Canada)',
    'de-de': 'German (Germany)',
    'it-it': 'Italian (Italy)',
    'pt-pt': 'Portuguese (Portugal)',
    'pt-br': 'Portuguese (Brazil)',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-cn': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)',
    'ar': 'Arabic',
    'hi': 'Hindi',
}


class TTS:
    def __init__(self):
        self.lang = 'ru'
        self.tld = 'ru'
        self.voice = 'ru'
        self.slow = False
        
    def generate_audio(self, text):
        try:
            tts = gTTS(text=text, lang=self.lang, tld=self.tld, slow=False)
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
            
    def set_language(self, lang_code):
        if lang_code in LANGUAGES:
            self.lang = lang_code
            self.tld = LANGUAGES[lang_code]['tld']
            self.voice = LANGUAGES[lang_code]['voices'][0]
            return True
        return False
        
    def set_voice(self, voice_code):
        # Проверяем, что голос принадлежит текущему языку
        if self.lang in LANGUAGES:
            if voice_code in LANGUAGES[self.lang]['voices']:
                self.voice = voice_code
                return True
        return False


tts = TTS()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Say Text", callback_data="speak")],
        [InlineKeyboardButton("Language", callback_data="language")],
        [InlineKeyboardButton("Voice", callback_data="voice")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    voice_name = VOICE_NAMES.get(tts.voice, tts.voice)
    lang_name = LANGUAGES.get(tts.lang, {}).get('name', tts.lang)
    
    await update.message.reply_text(
        f"TTS Bot\n\n"
        f"Language: {lang_name}\n"
        f"Voice: {voice_name}\n\n"
        f"Commands:\n"
        f"/gsay [text] - Speak text\n"
        f"/help - Help\n"
        f"/lang - Change language\n"
        f"/voice - Change voice\n\n"
        f"Send text and I will speak it.",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TTS Bot Guide\n\n"
        "Commands:\n"
        "/gsay [text] - Speak text\n"
        "   Example: /gsay Hello world\n\n"
        "/lang - Change language\n"
        "   Example: /lang ru\n\n"
        "/voice - Change voice\n"
        "   Example: /voice en-us\n\n"
        "/start - Main menu\n"
        "/help - This help\n\n"
        "Available languages:\n"
        + "\n".join([f"  {code}: {info['name']}" for code, info in LANGUAGES.items()])
    )


async def gsay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /gsay Hello world")
        return
        
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text}")
    
    audio = tts.generate_audio(text)
    if audio:
        voice_name = VOICE_NAMES.get(tts.voice, tts.voice)
        lang_name = LANGUAGES.get(tts.lang, {}).get('name', tts.lang)
        await update.message.reply_voice(
            voice=audio,
            caption=f"Language: {lang_name}\nVoice: {voice_name}"
        )
    else:
        await update.message.reply_text("Error generating audio")


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        # Если указан язык в аргументах
        lang_code = context.args[0].lower()
        if lang_code in LANGUAGES:
            tts.set_language(lang_code)
            lang_name = LANGUAGES[lang_code]['name']
            await update.message.reply_text(f"Language changed to: {lang_name}")
            return
        else:
            await update.message.reply_text(f"Language '{lang_code}' not found")
    
    # Показываем кнопки выбора языка
    keyboard = []
    row = []
    for code, info in LANGUAGES.items():
        if len(row) == 3:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(info['name'], callback_data=f"lang_{code}"))
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Current language: {LANGUAGES.get(tts.lang, {}).get('name', tts.lang)}\n\nSelect language:",
        reply_markup=reply_markup
    )


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        # Если указан голос в аргументах
        voice_code = context.args[0].lower()
        if tts.set_voice(voice_code):
            voice_name = VOICE_NAMES.get(voice_code, voice_code)
            await update.message.reply_text(f"Voice changed to: {voice_name}")
            return
        else:
            await update.message.reply_text(f"Voice '{voice_code}' not found for current language")
    
    # Показываем кнопки выбора голоса
    current_lang = tts.lang
    if current_lang in LANGUAGES:
        voices = LANGUAGES[current_lang]['voices']
        keyboard = []
        row = []
        for voice_code in voices:
            if len(row) == 2:
                keyboard.append(row)
                row = []
            voice_name = VOICE_NAMES.get(voice_code, voice_code)
            row.append(InlineKeyboardButton(voice_name, callback_data=f"voice_{voice_code}"))
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("Back", callback_data="back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        current_voice_name = VOICE_NAMES.get(tts.voice, tts.voice)
        await update.message.reply_text(
            f"Current voice: {current_voice_name}\n\nSelect voice:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("No voices available for current language")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith('/'):
        return
        
    audio = tts.generate_audio(text)
    if audio:
        voice_name = VOICE_NAMES.get(tts.voice, tts.voice)
        lang_name = LANGUAGES.get(tts.lang, {}).get('name', tts.lang)
        await update.message.reply_voice(
            voice=audio,
            caption=f"Language: {lang_name}\nVoice: {voice_name}"
        )
    else:
        await update.message.reply_text("Error generating audio")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "speak":
        await query.edit_message_text("Send text and I will speak it.")
        
    elif data == "language":
        # Показываем кнопки выбора языка
        keyboard = []
        row = []
        for code, info in LANGUAGES.items():
            if len(row) == 3:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(info['name'], callback_data=f"lang_{code}"))
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("Back", callback_data="back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Current language: {LANGUAGES.get(tts.lang, {}).get('name', tts.lang)}\n\nSelect language:",
            reply_markup=reply_markup
        )
        
    elif data == "voice":
        # Показываем кнопки выбора голоса
        current_lang = tts.lang
        if current_lang in LANGUAGES:
            voices = LANGUAGES[current_lang]['voices']
            keyboard = []
            row = []
            for voice_code in voices:
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
                voice_name = VOICE_NAMES.get(voice_code, voice_code)
                row.append(InlineKeyboardButton(voice_name, callback_data=f"voice_{voice_code}"))
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Back", callback_data="back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            current_voice_name = VOICE_NAMES.get(tts.voice, tts.voice)
            await query.edit_message_text(
                f"Current voice: {current_voice_name}\n\nSelect voice:",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("No voices available")
            
    elif data.startswith("lang_"):
        lang_code = data.split("_")[1]
        if tts.set_language(lang_code):
            lang_name = LANGUAGES[lang_code]['name']
            await query.edit_message_text(f"Language changed to: {lang_name}")
        else:
            await query.edit_message_text("Error changing language")
            
    elif data.startswith("voice_"):
        voice_code = data.split("_")[1]
        if tts.set_voice(voice_code):
            voice_name = VOICE_NAMES.get(voice_code, voice_code)
            await query.edit_message_text(f"Voice changed to: {voice_name}")
        else:
            await query.edit_message_text("Error changing voice")
            
    elif data == "back":
        # Возврат в главное меню
        keyboard = [
            [InlineKeyboardButton("Say Text", callback_data="speak")],
            [InlineKeyboardButton("Language", callback_data="language")],
            [InlineKeyboardButton("Voice", callback_data="voice")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        voice_name = VOICE_NAMES.get(tts.voice, tts.voice)
        lang_name = LANGUAGES.get(tts.lang, {}).get('name', tts.lang)
        
        await query.edit_message_text(
            f"TTS Bot\n\n"
            f"Language: {lang_name}\n"
            f"Voice: {voice_name}\n\n"
            f"Commands:\n"
            f"/gsay [text] - Speak text\n"
            f"/help - Help\n"
            f"/lang - Change language\n"
            f"/voice - Change voice\n\n"
            f"Send text and I will speak it.",
            reply_markup=reply_markup
        )


async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I can only process text messages. Send text to speak.")


def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Команды
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("gsay", gsay_command))
        application.add_handler(CommandHandler("lang", lang_command))
        application.add_handler(CommandHandler("voice", voice_command))
        
        # Обработчики
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.VOICE, voice_message_handler))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Список команд для меню Telegram
        commands = [
            ("start", "Menu"),
            ("help", "Help"),
            ("gsay", "Say text"),
            ("lang", "Change language"),
            ("voice", "Change voice"),
        ]
        application.bot.set_my_commands(commands)
        
        logger.info("Bot started!")
        print("TTS Bot started!")
        print(f"Available languages: {len(LANGUAGES)}")
        print(f"Commands: /gsay, /help, /lang, /voice")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
