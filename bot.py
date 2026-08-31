import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import samtts

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)

class SamTTSWrapper:
    def __init__(self):
        self.sam = samtts.SamTTS()
    
    def speak(self, text):
        audio_bytes = io.BytesIO()
        self.sam.save(audio_bytes, text)
        audio_bytes.seek(0)
        return audio_bytes

tts = SamTTSWrapper()

async def start(update, context):
    await update.message.reply_text("SAM TTS Bot\nUse /gsay [text]")

async def gsay_command(update, context):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /gsay Hello")
        return
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text[:50]}...")
    audio = tts.speak(text)
    if audio:
        await update.message.reply_voice(voice=audio, caption="Voice: Sam")
    else:
        await update.message.reply_text("Error")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gsay", gsay_command))
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
