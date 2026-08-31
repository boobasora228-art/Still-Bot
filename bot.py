import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from gtts import gTTS

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VOICE_PRESETS = {
    'sam': {
        'name': 'Sam (US Male)',
        'lang': 'en',
        'tld': 'us',
        'slow': False,
        'description': 'American English male voice'
    },
    'mike': {
        'name': 'Mike (UK Male)',
        'lang': 'en',
        'tld': 'co.uk',
        'slow': False,
        'description': 'British English male voice'
    },
    'mary': {
        'name': 'Mary (US Female)',
        'lang': 'en',
        'tld': 'us',
        'slow': False,
        'description': 'American English female voice'
    },
    'robot': {
        'name': 'Robot',
        'lang': 'en',
        'tld': 'us',
        'slow': False,
        'description': 'Fast robotic voice'
    },
    'elf': {
        'name': 'Elf',
        'lang': 'en',
        'tld': 'us',
        'slow': False,
        'description': 'High pitched voice'
    },
    'old_man': {
        'name': 'Old Man',
        'lang': 'en',
        'tld': 'us',
        'slow': True,
        'description': 'Slow deep voice'
    },
    'russian': {
        'name': 'Russian Voice',
        'lang': 'ru',
        'tld': 'ru',
        'slow': False,
        'description': 'Russian language voice'
    },
    'french': {
        'name': 'French Voice',
        'lang': 'fr',
        'tld': 'fr',
        'slow': False,
        'description': 'French language voice'
    },
    'german': {
        'name': 'German Voice',
        'lang': 'de',
        'tld': 'de',
        'slow': False,
        'description': 'German language voice'
    },
    'spanish': {
        'name': 'Spanish Voice',
        'lang': 'es',
        'tld': 'es',
        'slow': False,
        'description': 'Spanish language voice'
    },
    'italian': {
        'name': 'Italian Voice',
        'lang': 'it',
        'tld': 'it',
        'slow': False,
        'description': 'Italian language voice'
    },
    'japanese': {
        'name': 'Japanese Voice',
        'lang': 'ja',
        'tld': 'co.jp',
        'slow': False,
        'description': 'Japanese language voice'
    },
    'chinese': {
        'name': 'Chinese Voice',
        'lang': 'zh',
        'tld': 'cn',
        'slow': False,
        'description': 'Chinese language voice'
    },
}


class GoogleTTSBot:
    def __init__(self):
        self.current_voice = 'sam'
        self.voice_params = VOICE_PRESETS['sam'].copy()
    
    def set_voice(self, voice_name):
        if voice_name in VOICE_PRESETS:
            self.current_voice = voice_name
            self.voice_params = VOICE_PRESETS[voice_name].copy()
            return True
        return False
    
    def speak(self, text):
        try:
            tts = gTTS(
                text=text,
                lang=self.voice_params['lang'],
                tld=self.voice_params['tld'],
                slow=self.voice_params['slow']
            )
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None


tts_bot = GoogleTTSBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sam (US Male)", callback_data="voice_sam"),
         InlineKeyboardButton("Mike (UK Male)", callback_data="voice_mike"),
         InlineKeyboardButton("Mary (US Female)", callback_data="voice_mary")],
        [InlineKeyboardButton("Robot", callback_data="voice_robot"),
         InlineKeyboardButton("Elf", callback_data="voice_elf"),
         InlineKeyboardButton("Old Man", callback_data="voice_old_man")],
        [InlineKeyboardButton("Russian", callback_data="voice_russian"),
         InlineKeyboardButton("French", callback_data="voice_french"),
         InlineKeyboardButton("German", callback_data="voice_german")],
        [InlineKeyboardButton("Spanish", callback_data="voice_spanish"),
         InlineKeyboardButton("Italian", callback_data="voice_italian"),
         InlineKeyboardButton("Japanese", callback_data="voice_japanese")],
        [InlineKeyboardButton("Chinese", callback_data="voice_chinese")],
        [InlineKeyboardButton("Help", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_voice = VOICE_PRESETS[tts_bot.current_voice]['name']
    
    await update.message.reply_text(
        f"Google TTS Bot\n\n"
        f"Current voice: {current_voice}\n"
        f"Language: {tts_bot.voice_params['lang']}\n"
        f"Slow mode: {tts_bot.voice_params['slow']}\n\n"
        f"Use /gsay [text] to speak\n"
        f"Example: /gsay Hello world\n\n"
        f"Select voice from buttons below:",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help\n\n"
        "Commands:\n"
        "/gsay [text] - Speak text\n"
        "   Example: /gsay Hello world\n"
        "/start - Main menu\n"
        "/help - This help\n\n"
        "Available voices:\n"
        + "\n".join([f"- {v['name']}" for k, v in VOICE_PRESETS.items()])
    )


async def gsay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /gsay Hello world")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text[:50]}...")
    
    audio = tts_bot.speak(text)
    
    if audio:
        voice_name = VOICE_PRESETS[tts_bot.current_voice]['name']
        await update.message.reply_voice(
            voice=audio,
            caption=f"Voice: {voice_name}"
        )
    else:
        await update.message.reply_text("Error generating audio")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith('/'):
        return
    
    await update.message.reply_text(
        "Use /gsay [text] to speak.\n"
        "Example: /gsay Hello world"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        await query.edit_message_text(
            "Help\n\n"
            "Use /gsay [text] to speak\n\n"
            "Commands:\n"
            "/gsay [text] - Speak\n"
            "/start - Menu\n"
            "/help - Help\n\n"
            "Select voice from menu",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])
        )
        return
    
    if data == "back":
        await start(update, context)
        return
    
    if data.startswith("voice_"):
        voice_name = data.split("_")[1]
        if tts_bot.set_voice(voice_name):
            voice_display = VOICE_PRESETS[voice_name]['name']
            await query.edit_message_text(f"Voice changed to: {voice_display}")
        else:
            await query.edit_message_text("Error changing voice")
        return


def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("gsay", gsay_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        commands = [
            ("start", "Menu"),
            ("help", "Help"),
            ("gsay", "Say text"),
        ]
        application.bot.set_my_commands(commands)
        
        logger.info("Bot started!")
        print("\n" + "="*50)
        print("Google TTS Bot started!")
        print(f"Available voices: {len(VOICE_PRESETS)}")
        print("Use /gsay [text] to speak")
        print("="*50 + "\n")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
