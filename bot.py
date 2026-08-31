import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from gtts import gTTS

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Голоса Google TTS (разные акценты)
VOICES = {
    'sam': {'name': 'Sam (US Male)', 'lang': 'en', 'tld': 'us', 'slow': False},
    'mike': {'name': 'Mike (UK Male)', 'lang': 'en', 'tld': 'co.uk', 'slow': False},
    'mary': {'name': 'Mary (US Female)', 'lang': 'en', 'tld': 'us', 'slow': False},
    'robot': {'name': 'Robot (Fast)', 'lang': 'en', 'tld': 'us', 'slow': False},
    'elf': {'name': 'Elf (High)', 'lang': 'en', 'tld': 'us', 'slow': False},
    'old_man': {'name': 'Old Man (Slow)', 'lang': 'en', 'tld': 'us', 'slow': True},
    'russian': {'name': 'Russian', 'lang': 'ru', 'tld': 'ru', 'slow': False},
    'french': {'name': 'French', 'lang': 'fr', 'tld': 'fr', 'slow': False},
    'german': {'name': 'German', 'lang': 'de', 'tld': 'de', 'slow': False},
    'spanish': {'name': 'Spanish', 'lang': 'es', 'tld': 'es', 'slow': False},
    'italian': {'name': 'Italian', 'lang': 'it', 'tld': 'it', 'slow': False},
    'japanese': {'name': 'Japanese', 'lang': 'ja', 'tld': 'co.jp', 'slow': False},
    'chinese': {'name': 'Chinese', 'lang': 'zh', 'tld': 'cn', 'slow': False},
}

class TTSBot:
    def __init__(self):
        self.current_voice = 'sam'
    
    def set_voice(self, voice_name):
        if voice_name in VOICES:
            self.current_voice = voice_name
            return True
        return False
    
    def speak(self, text):
        try:
            params = VOICES[self.current_voice]
            tts = gTTS(
                text=text,
                lang=params['lang'],
                tld=params['tld'],
                slow=params['slow']
            )
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

tts = TTSBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sam (US)", callback_data="voice_sam"),
         InlineKeyboardButton("Mike (UK)", callback_data="voice_mike"),
         InlineKeyboardButton("Mary (US)", callback_data="voice_mary")],
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
    
    current = VOICES[tts.current_voice]['name']
    
    await update.message.reply_text(
        f"Google TTS Bot\n\n"
        f"Current voice: {current}\n\n"
        f"Use /gsay [text] to speak\n"
        f"Example: /gsay Hello world",
        reply_markup=reply_markup
    )

async def gsay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /gsay Hello world")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text[:50]}...")
    
    audio = tts.speak(text)
    if audio:
        voice_name = VOICES[tts.current_voice]['name']
        await update.message.reply_voice(voice=audio, caption=f"Voice: {voice_name}")
    else:
        await update.message.reply_text("Error generating audio")

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        voices_list = "\n".join([f"- {k}: {v['name']}" for k, v in VOICES.items()])
        await update.message.reply_text(
            f"Current: {VOICES[tts.current_voice]['name']}\n\nAvailable:\n{voices_list}\n\nUse /voice [name]"
        )
        return
    
    voice_name = context.args[0].lower()
    if tts.set_voice(voice_name):
        await update.message.reply_text(f"Voice changed to: {VOICES[voice_name]['name']}")
    else:
        await update.message.reply_text(f"Voice '{voice_name}' not found")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await query.edit_message_text(
            "Help\n\nCommands:\n/gsay [text] - Speak\n/voice [name] - Change voice\n/start - Menu",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])
        )
        return
    
    if query.data == "back":
        await start(update, context)
        return
    
    if query.data.startswith("voice_"):
        voice_name = query.data.split("_")[1]
        if tts.set_voice(voice_name):
            await query.edit_message_text(f"Voice changed to: {VOICES[voice_name]['name']}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gsay", gsay_command))
    app.add_handler(CommandHandler("voice", voice_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    app.bot.set_my_commands([
        ("start", "Menu"),
        ("gsay", "Say text"),
        ("voice", "Change voice")
    ])
    
    print("Google TTS Bot started!")
    print(f"Available voices: {len(VOICES)}")
    app.run_polling()

if __name__ == "__main__":
    main()
