import logging
import pyttsx3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WindowsTTS:
    def __init__(self):
        self.engine = None
        self.voices = []
        self.voice_names = []
        self.current_voice = 0
        self.rate = 200
        self.volume = 1.0
        self.init_engine()
        self.list_voices()
        
    def init_engine(self):
        try:
            self.engine = pyttsx3.init('sapi5')
            self.voices = self.engine.getProperty('voices')
            logger.info(f"TTS initialized, found {len(self.voices)} voices")
        except Exception as e:
            logger.error(f"TTS init error: {e}")
            self.engine = None
                
    def list_voices(self):
        self.voice_names = []
        if self.engine is None:
            return
        try:
            for i, voice in enumerate(self.voices):
                name = voice.name
                self.voice_names.append(name)
                logger.info(f"Voice {i}: {name}")
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            
    def set_voice(self, index):
        if self.engine is None:
            return False
        try:
            if index < len(self.voices):
                self.engine.setProperty('voice', self.voices[index].id)
                self.current_voice = index
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
            
    def speak(self, text):
        if self.engine is None:
            logger.error("TTS engine not initialized")
            return False
        try:
            logger.info(f"Speaking: {text}")
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Speaking error: {e}")
            return False


tts = WindowsTTS()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Speak Message", callback_data="speak")],
        [InlineKeyboardButton("Voice Settings", callback_data="settings")],
        [InlineKeyboardButton("List Voices", callback_data="list_voices")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    voice_name = tts.voice_names[tts.current_voice] if tts.voice_names else "Unknown"
    
    await update.message.reply_text(
        f"Windows TTS Bot\n\n"
        f"Send me text and I will speak it.\n\n"
        f"Current Voice: {voice_name}\n"
        f"Rate: {tts.rate}\n"
        f"Volume: {int(tts.volume * 100)}%\n\n"
        f"Commands:\n"
        f"/start - Main menu\n"
        f"/help - Help\n"
        f"/voices - List voices\n"
        f"/voice [number] - Select voice\n"
        f"/rate [100-300] - Speed\n"
        f"/volume [0-100] - Volume\n"
        f"/speak [text] - Speak text",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Main menu\n"
        "/help - Help\n"
        "/voices - List voices\n"
        "/voice [number] - Select voice\n"
        "/rate [100-300] - Set speed\n"
        "/volume [0-100] - Set volume\n"
        "/speak [text] - Speak text\n\n"
        "Example: /speak Hello world"
    )


async def voices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tts.voice_names:
        await update.message.reply_text("No voices found")
        return
        
    text = "Available Voices:\n\n"
    for i, name in enumerate(tts.voice_names):
        marker = "-> " if i == tts.current_voice else "   "
        text += f"{marker} {i}: {name}\n"
    
    await update.message.reply_text(text)


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Specify voice number. Example: /voice 2")
        return
        
    try:
        index = int(context.args[0])
        if tts.set_voice(index):
            await update.message.reply_text(f"Voice changed to: {tts.voice_names[index]}")
        else:
            await update.message.reply_text(f"Voice with index {index} not found")
    except ValueError:
        await update.message.reply_text("Enter a number. Example: /voice 2")


async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Current rate: {tts.rate}. Use /rate [100-300]")
        return
        
    try:
        rate = int(context.args[0])
        rate = max(50, min(300, rate))
        tts.rate = rate
        await update.message.reply_text(f"Rate changed to: {rate}")
    except ValueError:
        await update.message.reply_text("Enter a number. Example: /rate 200")


async def volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Current volume: {int(tts.volume * 100)}%. Use /volume [0-100]")
        return
        
    try:
        volume = int(context.args[0])
        volume = max(0, min(100, volume))
        tts.volume = volume / 100
        await update.message.reply_text(f"Volume changed to: {volume}%")
    except ValueError:
        await update.message.reply_text("Enter a number. Example: /volume 80")


async def speak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Enter text. Example: /speak Hello world")
        return
        
    text = " ".join(context.args)
    await update.message.reply_text(f"Speaking: {text}")
    
    import threading
    def speak_thread():
        tts.speak(text)
    threading.Thread(target=speak_thread, daemon=True).start()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith('/'):
        return
        
    await update.message.reply_text(f"Speaking: {text[:50]}...")
    
    import threading
    def speak_thread():
        tts.speak(text)
    threading.Thread(target=speak_thread, daemon=True).start()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "speak":
        await query.edit_message_text("Send me text and I will speak it.")
        
    elif data == "settings":
        keyboard = [
            [InlineKeyboardButton("Rate +10", callback_data="rate_up")],
            [InlineKeyboardButton("Rate -10", callback_data="rate_down")],
            [InlineKeyboardButton("Volume +10%", callback_data="volume_up")],
            [InlineKeyboardButton("Volume -10%", callback_data="volume_down")],
            [InlineKeyboardButton("Back", callback_data="back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        voice_name = tts.voice_names[tts.current_voice] if tts.voice_names else "Unknown"
        
        await query.edit_message_text(
            f"Voice Settings:\n\n"
            f"Current Voice: {voice_name}\n"
            f"Rate: {tts.rate}\n"
            f"Volume: {int(tts.volume * 100)}%",
            reply_markup=reply_markup
        )
        
    elif data == "list_voices":
        if not tts.voice_names:
            await query.edit_message_text("No voices found")
            return
            
        text = "Available Voices:\n\n"
        for i, name in enumerate(tts.voice_names):
            marker = "-> " if i == tts.current_voice else "   "
            text += f"{marker} {i}: {name}\n"
        
        keyboard = [[InlineKeyboardButton("Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    elif data == "rate_up":
        tts.rate = min(300, tts.rate + 10)
        await query.edit_message_text(f"Rate: {tts.rate}")
        
    elif data == "rate_down":
        tts.rate = max(50, tts.rate - 10)
        await query.edit_message_text(f"Rate: {tts.rate}")
        
    elif data == "volume_up":
        tts.volume = min(1.0, tts.volume + 0.1)
        await query.edit_message_text(f"Volume: {int(tts.volume * 100)}%")
        
    elif data == "volume_down":
        tts.volume = max(0, tts.volume - 0.1)
        await query.edit_message_text(f"Volume: {int(tts.volume * 100)}%")
        
    elif data == "back":
        await start(update, context)


def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("voices", voices_command))
        application.add_handler(CommandHandler("voice", voice_command))
        application.add_handler(CommandHandler("rate", rate_command))
        application.add_handler(CommandHandler("volume", volume_command))
        application.add_handler(CommandHandler("speak", speak_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("Bot started!")
        print("Bot started!")
        print(f"Available voices: {len(tts.voice_names)}")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
