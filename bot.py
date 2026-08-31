import logging
import io
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Бесплатный API для генерации голоса SAM (через TTS)
# Используем API от VoiceMaker или другие бесплатные сервисы

class SamTTSOnline:
    def __init__(self):
        self.current_voice = 'sam'
        self.voices = {
            'sam': {'name': 'Sam', 'voice_id': 'en-US-SamNeural'},
            'mike': {'name': 'Mike', 'voice_id': 'en-US-MikeNeural'},
            'mary': {'name': 'Mary', 'voice_id': 'en-US-MaryNeural'},
        }
    
    def set_voice(self, voice_name):
        if voice_name in self.voices:
            self.current_voice = voice_name
            return True
        return False
    
    def speak(self, text):
        try:
            # Используем бесплатный API от StreamElements
            response = requests.post(
                "https://api.streamelements.com/kappa/v2/speech",
                json={
                    "text": text,
                    "voice": "Brian"  # Brian - голос похожий на Sam
                },
                timeout=10
            )
            
            if response.status_code == 200:
                audio_bytes = io.BytesIO(response.content)
                audio_bytes.seek(0)
                return audio_bytes
            else:
                logger.error(f"API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

tts = SamTTSOnline()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sam", callback_data="voice_sam"),
         InlineKeyboardButton("Mike", callback_data="voice_mike"),
         InlineKeyboardButton("Mary", callback_data="voice_mary")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"SAM TTS Bot (Online)\n\n"
        f"Current voice: {tts.voices[tts.current_voice]['name']}\n\n"
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
        voice_name = tts.voices[tts.current_voice]['name']
        await update.message.reply_voice(voice=audio, caption=f"Voice: {voice_name}")
    else:
        await update.message.reply_text("Error generating audio. Please try again.")

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Available: sam, mike, mary")
        return
    
    voice_name = context.args[0].lower()
    if tts.set_voice(voice_name):
        await update.message.reply_text(f"Voice changed to: {tts.voices[voice_name]['name']}")
    else:
        await update.message.reply_text(f"Voice '{voice_name}' not found")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("voice_"):
        voice_name = query.data.split("_")[1]
        if tts.set_voice(voice_name):
            await query.edit_message_text(f"Voice changed to: {tts.voices[voice_name]['name']}")
        return

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
    
    print("Bot started! Use /gsay [text]")
    app.run_polling()

if __name__ == "__main__":
    main()
