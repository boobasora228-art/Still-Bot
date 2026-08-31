import logging
import io
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SamTTSOnline:
    def __init__(self):
        self.current_voice = 'sam'
        self.voices = {
            'sam': {'name': 'Sam', 'speed': 72, 'pitch': 64, 'throat': 128, 'mouth': 128},
            'mike': {'name': 'Mike', 'speed': 70, 'pitch': 50, 'throat': 150, 'mouth': 120},
            'mary': {'name': 'Mary', 'speed': 75, 'pitch': 90, 'throat': 100, 'mouth': 140},
            'robot': {'name': 'Robot', 'speed': 92, 'pitch': 60, 'throat': 190, 'mouth': 190},
            'elf': {'name': 'Elf', 'speed': 72, 'pitch': 64, 'throat': 110, 'mouth': 160},
            'old_man': {'name': 'Old Man', 'speed': 82, 'pitch': 72, 'throat': 110, 'mouth': 105},
            'alien': {'name': 'Alien', 'speed': 100, 'pitch': 64, 'throat': 150, 'mouth': 200},
        }
        self.api_url = "https://api.voicemaker.in/text-to-speech"  # Платный API
    
    def set_voice(self, voice_name):
        if voice_name in self.voices:
            self.current_voice = voice_name
            return True
        return False
    
    def speak(self, text):
        try:
            # Используем бесплатный онлайн сервис
            # Для примера используем локальный генератор через заглушку
            from samtts import SamTTS
            tts = SamTTS()
            audio_bytes = io.BytesIO()
            tts.save(audio_bytes, text)
            audio_bytes.seek(0)
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

tts_bot = SamTTSOnline()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sam", callback_data="voice_sam"),
         InlineKeyboardButton("Mike", callback_data="voice_mike"),
         InlineKeyboardButton("Mary", callback_data="voice_mary")],
        [InlineKeyboardButton("Robot", callback_data="voice_robot"),
         InlineKeyboardButton("Elf", callback_data="voice_elf"),
         InlineKeyboardButton("Old Man", callback_data="voice_old_man")],
        [InlineKeyboardButton("Alien", callback_data="voice_alien")],
        [InlineKeyboardButton("Help", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"SAM TTS Bot (Online)\n\n"
        f"Current voice: {tts_bot.voices[tts_bot.current_voice]['name']}\n\n"
        f"Use /gsay [text] to speak\n"
        f"Example: /gsay Hello world\n\n"
        f"Note: This is a demo. Install samtts for full quality.",
        reply_markup=reply_markup
    )

async def gsay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /gsay Hello world")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text[:50]}...")
    
    audio = tts_bot.speak(text)
    if audio:
        voice_name = tts_bot.voices[tts_bot.current_voice]['name']
        await update.message.reply_voice(voice=audio, caption=f"Voice: {voice_name}")
    else:
        await update.message.reply_text("Error generating audio. Try installing samtts.")

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Available: sam, mike, mary, robot, elf, old_man, alien")
        return
    
    voice_name = context.args[0].lower()
    if tts_bot.set_voice(voice_name):
        await update.message.reply_text(f"Voice changed to: {tts_bot.voices[voice_name]['name']}")
    else:
        await update.message.reply_text(f"Voice '{voice_name}' not found")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("voice_"):
        voice_name = query.data.split("_")[1]
        if tts_bot.set_voice(voice_name):
            await query.edit_message_text(f"Voice changed to: {tts_bot.voices[voice_name]['name']}")
        return
    
    if query.data == "help":
        await query.edit_message_text(
            "Help\n\nCommands:\n/gsay [text] - Speak\n/voice [name] - Change voice\n/start - Menu",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])
        )
        return
    
    if query.data == "back":
        await start(update, context)
        return

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gsay", gsay_command))
    app.add_handler(CommandHandler("voice", voice_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    app.bot.set_my_commands([("start", "Menu"), ("gsay", "Say text"), ("voice", "Change voice")])
    
    print("Bot started! Use /gsay [text]")
    app.run_polling()

if __name__ == "__main__":
    main()
