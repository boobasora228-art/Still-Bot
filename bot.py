import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from gtts import gTTS
import pyttsx3

TOKEN = "8716430991:AAF7h4RZNaNNfc1_X4ScSVeVp-jmwwq4JBs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SAPI 4 через msspeechapi4 ---
try:
    from msspeechapi4 import SAPI4
    SAPI4_AVAILABLE = True
    logger.info("SAPI 4 loaded")
except ImportError:
    SAPI4_AVAILABLE = False
    logger.warning("SAPI 4 not found")

# --- SAPI 5 через pyttsx3 ---
try:
    sapi5_engine = pyttsx3.init('sapi5')
    sapi5_voices = sapi5_engine.getProperty('voices')
    SAPI5_AVAILABLE = True
    logger.info(f"SAPI 5 loaded, voices: {len(sapi5_voices)}")
except Exception as e:
    SAPI5_AVAILABLE = False
    logger.warning(f"SAPI 5 error: {e}")

# --- Google TTS ---
GTT_AVAILABLE = True

# Доступные языки для Google TTS
LANGUAGES = {
    'ru': 'Russian',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'ar': 'Arabic',
    'hi': 'Hindi',
}


class TTSBot:
    def __init__(self):
        self.engine_type = 'google'  # google, sapi4, sapi5
        self.lang = 'ru'
        self.tld = 'ru'
        self.voice_index = 0
        self.sapi4_engine = None
        self.sapi4_voices = []
        self.sapi5_engine = None
        self.sapi5_voices = []
        
        # Инициализация SAPI 4
        if SAPI4_AVAILABLE:
            try:
                self.sapi4_engine = SAPI4()
                self.sapi4_voices = self.sapi4_engine.get_voices()
                logger.info(f"SAPI 4 voices: {len(self.sapi4_voices)}")
            except Exception as e:
                logger.error(f"SAPI 4 init error: {e}")
                self.sapi4_engine = None
        
        # Инициализация SAPI 5
        if SAPI5_AVAILABLE:
            try:
                self.sapi5_engine = pyttsx3.init('sapi5')
                self.sapi5_voices = self.sapi5_engine.getProperty('voices')
                logger.info(f"SAPI 5 voices: {len(self.sapi5_voices)}")
            except Exception as e:
                logger.error(f"SAPI 5 init error: {e}")
                self.sapi5_engine = None
        
        # Выбор движка по умолчанию
        if SAPI4_AVAILABLE:
            self.engine_type = 'sapi4'
        elif SAPI5_AVAILABLE:
            self.engine_type = 'sapi5'
        else:
            self.engine_type = 'google'
    
    def get_engines(self):
        """Список доступных движков"""
        engines = []
        if SAPI4_AVAILABLE:
            engines.append(('sapi4', 'SAPI 4 (Sam, Mike, Mary)'))
        if SAPI5_AVAILABLE:
            engines.append(('sapi5', 'SAPI 5 (David, Zira)'))
        if GTT_AVAILABLE:
            engines.append(('google', 'Google TTS'))
        return engines
    
    def get_voices(self):
        """Список голосов для текущего движка"""
        voices = []
        if self.engine_type == 'sapi4' and self.sapi4_engine:
            try:
                for i, voice in enumerate(self.sapi4_voices):
                    name = str(voice)
                    voices.append((i, name))
            except Exception as e:
                logger.error(f"SAPI 4 voices error: {e}")
        elif self.engine_type == 'sapi5' and self.sapi5_engine:
            try:
                for i, voice in enumerate(self.sapi5_voices):
                    name = voice.name
                    voices.append((i, name))
            except Exception as e:
                logger.error(f"SAPI 5 voices error: {e}")
        else:
            # Google TTS - языки
            for i, (code, name) in enumerate(LANGUAGES.items()):
                voices.append((i, f"Google {name} ({code})"))
        return voices
    
    def set_engine(self, engine_type):
        """Сменить движок"""
        engines = [e[0] for e in self.get_engines()]
        if engine_type in engines:
            self.engine_type = engine_type
            self.voice_index = 0
            return True
        return False
    
    def set_voice(self, index):
        """Сменить голос"""
        voices = self.get_voices()
        if 0 <= index < len(voices):
            self.voice_index = index
            return True
        return False
    
    def set_language(self, lang_code):
        """Сменить язык для Google TTS"""
        if lang_code in LANGUAGES:
            self.lang = lang_code
            self.tld = lang_code
            return True
        return False
    
    def speak(self, text):
        """Озвучивание текста"""
        try:
            if self.engine_type == 'sapi4' and self.sapi4_engine:
                voices = self.sapi4_engine.get_voices()
                if voices and self.voice_index < len(voices):
                    self.sapi4_engine.set_voice(voices[self.voice_index])
                self.sapi4_engine.speak(text)
                return True
                
            elif self.engine_type == 'sapi5' and self.sapi5_engine:
                if self.voice_index < len(self.sapi5_voices):
                    self.sapi5_engine.setProperty('voice', self.sapi5_voices[self.voice_index].id)
                self.sapi5_engine.say(text)
                self.sapi5_engine.runAndWait()
                return True
                
            else:  # google
                audio = self.generate_audio(text)
                return audio
                
        except Exception as e:
            logger.error(f"Speak error: {e}")
            return None
    
    def generate_audio(self, text):
        """Генерация аудио через Google TTS"""
        try:
            tts = gTTS(text=text, lang=self.lang, tld=self.tld, slow=False)
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            return audio_bytes
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return None


# --- Создаем экземпляр ---
tts_bot = TTSBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engines = tts_bot.get_engines()
    
    # Кнопки движков
    keyboard = []
    for eng_type, eng_name in engines:
        marker = "✅ " if eng_type == tts_bot.engine_type else ""
        keyboard.append([InlineKeyboardButton(
            f"{marker}{eng_name}",
            callback_data=f"engine_{eng_type}"
        )])
    
    keyboard.append([InlineKeyboardButton("🎤 Voices", callback_data="voices")])
    keyboard.append([InlineKeyboardButton("🌍 Language (Google)", callback_data="language")])
    keyboard.append([InlineKeyboardButton("❓ Help", callback_data="help")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Текущий голос
    voice_name = "Unknown"
    voices = tts_bot.get_voices()
    if voices and tts_bot.voice_index < len(voices):
        voice_name = voices[tts_bot.voice_index][1]
    
    engine_name = dict(tts_bot.get_engines()).get(tts_bot.engine_type, tts_bot.engine_type.upper())
    
    await update.message.reply_text(
        f"🎙 TTS Bot\n\n"
        f"Engine: {engine_name}\n"
        f"Voice: {voice_name}\n"
        f"Language: {LANGUAGES.get(tts_bot.lang, 'Russian')}\n\n"
        f"Use /gsay [text] to speak\n"
        f"Example: /gsay Hello world",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 TTS Bot Guide\n\n"
        "Commands:\n"
        "/gsay [text] - Speak text\n"
        "   Example: /gsay Hello world\n\n"
        "/start - Main menu\n"
        "/help - This help\n\n"
        "Engines:\n"
        "• SAPI 4 - Sam, Mike, Mary (Windows XP)\n"
        "• SAPI 5 - David, Zira (Modern Windows)\n"
        "• Google TTS - High quality online\n\n"
        "Use buttons in /start menu to change settings."
    )


async def gsay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Enter text. Example: /gsay Hello world")
        return
        
    text = " ".join(context.args)
    await update.message.reply_text(f"🔊 Speaking: {text[:50]}...")
    
    result = tts_bot.speak(text)
    
    if result is None:
        await update.message.reply_text("❌ Error generating audio")
    elif isinstance(result, io.BytesIO):
        # Google TTS - отправляем голосовое сообщение
        lang_name = LANGUAGES.get(tts_bot.lang, 'Russian')
        await update.message.reply_voice(
            voice=result,
            caption=f"🌍 Google TTS ({lang_name})"
        )
    elif result is True:
        # SAPI - уже озвучено локально
        await update.message.reply_text("✅ Done!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Игнорируем обычные сообщения (только /gsay)
    await update.message.reply_text(
        "📝 Use /gsay [text] to speak.\n"
        "Example: /gsay Hello world"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        await query.edit_message_text(
            "📖 Help\n\n"
            "Use /gsay [text] to speak\n\n"
            "Commands:\n"
            "/gsay [text] - Speak\n"
            "/start - Menu\n"
            "/help - Help\n\n"
            "Press Back to return",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )
        return
    
    if data == "back":
        await start(update, context)
        return
        
    if data == "voices":
        voices = tts_bot.get_voices()
        if not voices:
            await query.edit_message_text("❌ No voices available")
            return
        
        keyboard = []
        for i, (idx, name) in enumerate(voices):
            marker = "✅ " if i == tts_bot.voice_index else ""
            display_name = name[:30] + "..." if len(name) > 30 else name
            keyboard.append([InlineKeyboardButton(
                f"{marker}{display_name}",
                callback_data=f"voice_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        current_voice = voices[tts_bot.voice_index][1] if voices else "None"
        await query.edit_message_text(
            f"🎤 Select voice\n\nCurrent: {current_voice}",
            reply_markup=reply_markup
        )
        return
        
    if data == "language":
        keyboard = []
        row = []
        for code, name in LANGUAGES.items():
            if len(row) == 3:
                keyboard.append(row)
                row = []
            marker = "✅ " if code == tts_bot.lang else ""
            row.append(InlineKeyboardButton(f"{marker}{name}", callback_data=f"lang_{code}"))
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🌍 Select language\n\nCurrent: {LANGUAGES.get(tts_bot.lang, 'Russian')}",
            reply_markup=reply_markup
        )
        return
        
    if data.startswith("engine_"):
        engine_type = data.split("_")[1]
        if tts_bot.set_engine(engine_type):
            engine_name = dict(tts_bot.get_engines()).get(engine_type, engine_type.upper())
            await query.edit_message_text(f"✅ Engine changed to: {engine_name}")
        else:
            await query.edit_message_text("❌ Error changing engine")
        return
        
    if data.startswith("voice_"):
        try:
            index = int(data.split("_")[1])
            if tts_bot.set_voice(index):
                voices = tts_bot.get_voices()
                voice_name = voices[index][1] if voices else "Unknown"
                await query.edit_message_text(f"✅ Voice changed to: {voice_name}")
            else:
                await query.edit_message_text("❌ Error changing voice")
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
            
    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        if tts_bot.set_language(lang_code):
            lang_name = LANGUAGES[lang_code]
            await query.edit_message_text(f"✅ Language changed to: {lang_name}")
        else:
            await query.edit_message_text("❌ Error changing language")
        return


def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Команды
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("gsay", gsay_command))
        
        # Обработчики
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Список команд для меню Telegram
        commands = [
            ("start", "Menu"),
            ("help", "Help"),
            ("gsay", "Say text"),
        ]
        application.bot.set_my_commands(commands)
        
        logger.info("Bot started!")
        print("\n" + "="*50)
        print("🎙 TTS Bot started!")
        print(f"Engines available: {[e[0] for e in tts_bot.get_engines()]}")
        print(f"Default engine: {tts_bot.engine_type}")
        print("Use /gsay [text] to speak")
        print("="*50 + "\n")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
