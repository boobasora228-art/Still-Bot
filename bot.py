import os
import logging
import pyttsx3
import win32com.client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# --- Конфигурация ---
TOKEN = "8659191729:AAFn0J4c5TLcwEIFpiM49Ln7-idqb3mJPyc"

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Класс для работы с SAPI 5 ---
class Sapi5TTS:
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
        """Инициализация SAPI 5"""
        try:
            self.engine = pyttsx3.init('sapi5')
            self.voices = self.engine.getProperty('voices')
            logger.info(f"SAPI 5 инициализирован, найдено {len(self.voices)} голосов")
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            try:
                # Альтернативный способ
                self.engine = win32com.client.Dispatch("SAPI.SpVoice")
                self.voices = self.engine.GetVoices()
                logger.info(f"SAPI через win32com, найдено {self.voices.Count} голосов")
            except Exception as e2:
                logger.error(f"Критическая ошибка: {e2}")
                self.engine = None
                
    def list_voices(self):
        """Список доступных голосов"""
        self.voice_names = []
        if self.engine is None:
            return
            
        try:
            if hasattr(self.engine, 'getProperty'):
                # pyttsx3
                for i, voice in enumerate(self.voices):
                    name = voice.name
                    self.voice_names.append(name)
                    logger.info(f"Голос {i}: {name}")
            else:
                # win32com
                for i in range(self.voices.Count):
                    name = self.voices[i].GetDescription()
                    self.voice_names.append(name)
                    logger.info(f"Голос {i}: {name}")
        except Exception as e:
            logger.error(f"Ошибка получения списка голосов: {e}")
            
    def set_voice(self, index):
        """Установка голоса по индексу"""
        if self.engine is None:
            return False
            
        try:
            if hasattr(self.engine, 'setProperty'):
                # pyttsx3
                if index < len(self.voices):
                    self.engine.setProperty('voice', self.voices[index].id)
                    self.current_voice = index
                    return True
            else:
                # win32com
                if index < self.voices.Count:
                    self.engine.Voice = self.voices[index]
                    self.current_voice = index
                    return True
            return False
        except Exception as e:
            logger.error(f"Ошибка установки голоса: {e}")
            return False
            
    def set_voice_by_name(self, name):
        """Установка голоса по имени"""
        for i, voice_name in enumerate(self.voice_names):
            if name.lower() in voice_name.lower():
                return self.set_voice(i)
        return False
        
    def speak(self, text):
        """Озвучивание текста"""
        if self.engine is None:
            logger.error("TTS двигатель не инициализирован")
            return False
            
        try:
            logger.info(f"Озвучиваю: {text}")
            
            if hasattr(self.engine, 'setProperty'):
                # pyttsx3
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                # win32com
                self.engine.Rate = self.rate // 10
                self.engine.Volume = int(self.volume * 100)
                self.engine.Speak(text)
                
            return True
        except Exception as e:
            logger.error(f"Ошибка озвучивания: {e}")
            return False

    def get_voices_list(self):
        """Получить список голосов для кнопок"""
        buttons = []
        row = []
        for i, name in enumerate(self.voice_names):
            if len(row) == 2:
                buttons.append(row)
                row = []
            # Сокращаем длинные имена
            display_name = name[:20] + "..." if len(name) > 20 else name
            row.append(InlineKeyboardButton(display_name, callback_data=f"voice_{i}"))
        if row:
            buttons.append(row)
        return buttons


# --- Создаем экземпляр TTS ---
tts = Sapi5TTS()


# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        [InlineKeyboardButton("🎤 Озвучить сообщение", callback_data="speak")],
        [InlineKeyboardButton("🎵 Настройки голоса", callback_data="settings")],
        [InlineKeyboardButton("📋 Список голосов", callback_data="list_voices")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Голосовой ассистент SAPI 5\n\n"
        "Отправь мне текст, и я озвучу его через SAPI 5.\n"
        "Или используй кнопки ниже:\n\n"
        f"Текущий голос: {tts.voice_names[tts.current_voice] if tts.voice_names else 'Неизвестно'}\n"
        f"Скорость: {tts.rate}\n"
        f"Громкость: {int(tts.volume * 100)}%",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 Помощь:\n\n"
        "Просто отправь мне текст - я озвучу его.\n\n"
        "Команды:\n"
        "/start - Главное меню\n"
        "/help - Помощь\n"
        "/voices - Список голосов\n"
        "/voice [номер] - Выбрать голос\n"
        "/rate [число] - Скорость (100-300)\n"
        "/volume [0-100] - Громкость\n"
        "/speak [текст] - Озвучить текст"
    )


async def voices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /voices - показать список голосов"""
    if not tts.voice_names:
        await update.message.reply_text("❌ Голоса не найдены")
        return
        
    text = "📋 Доступные голоса:\n\n"
    for i, name in enumerate(tts.voice_names):
        marker = "👉 " if i == tts.current_voice else "   "
        text += f"{marker} {i}: {name}\n"
    
    text += f"\nТекущий голос: {tts.voice_names[tts.current_voice]}"
    
    await update.message.reply_text(text)


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /voice [номер] - выбрать голос"""
    if not context.args:
        await update.message.reply_text("❌ Укажите номер голоса. Пример: /voice 2")
        return
        
    try:
        index = int(context.args[0])
        if tts.set_voice(index):
            await update.message.reply_text(f"✅ Голос изменён на: {tts.voice_names[index]}")
        else:
            await update.message.reply_text(f"❌ Голос с номером {index} не найден")
    except ValueError:
        await update.message.reply_text("❌ Введите число. Пример: /voice 2")


async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rate [число] - скорость речи"""
    if not context.args:
        await update.message.reply_text(f"Текущая скорость: {tts.rate}. /rate [100-300]")
        return
        
    try:
        rate = int(context.args[0])
        rate = max(50, min(300, rate))
        tts.rate = rate
        await update.message.reply_text(f"✅ Скорость изменена: {rate}")
    except ValueError:
        await update.message.reply_text("❌ Введите число. Пример: /rate 200")


async def volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /volume [0-100] - громкость"""
    if not context.args:
        await update.message.reply_text(f"Текущая громкость: {int(tts.volume * 100)}%. /volume [0-100]")
        return
        
    try:
        volume = int(context.args[0])
        volume = max(0, min(100, volume))
        tts.volume = volume / 100
        await update.message.reply_text(f"✅ Громкость изменена: {volume}%")
    except ValueError:
        await update.message.reply_text("❌ Введите число. Пример: /volume 80")


async def speak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /speak [текст] - озвучить текст"""
    if not context.args:
        await update.message.reply_text("❌ Введите текст. Пример: /speak Привет мир!")
        return
        
    text = " ".join(context.args)
    await update.message.reply_text(f"🔊 Озвучиваю: {text}")
    
    # Озвучиваем в отдельном потоке, чтобы не блокировать бота
    import threading
    def speak_thread():
        tts.speak(text)
    threading.Thread(target=speak_thread, daemon=True).start()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text
    
    # Проверяем, не команда ли это
    if text.startswith('/'):
        return
        
    # Отвечаем, что озвучиваем
    await update.message.reply_text(f"🔊 Озвучиваю: {text[:50]}...")
    
    # Озвучиваем в отдельном потоке
    import threading
    def speak_thread():
        tts.speak(text)
    threading.Thread(target=speak_thread, daemon=True).start()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "speak":
        await query.edit_message_text(
            "✏️ Отправь мне текст, и я озвучу его!\n"
            "Или используй команду /speak [текст]"
        )
        
    elif data == "settings":
        keyboard = [
            [InlineKeyboardButton("➕ Скорость +10", callback_data="rate_up")],
            [InlineKeyboardButton("➖ Скорость -10", callback_data="rate_down")],
            [InlineKeyboardButton("➕ Громкость +10%", callback_data="volume_up")],
            [InlineKeyboardButton("➖ Громкость -10%", callback_data="volume_down")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎵 Настройки голоса:\n\n"
            f"Текущий голос: {tts.voice_names[tts.current_voice] if tts.voice_names else 'Неизвестно'}\n"
            f"Скорость: {tts.rate}\n"
            f"Громкость: {int(tts.volume * 100)}%",
            reply_markup=reply_markup
        )
        
    elif data == "list_voices":
        if not tts.voice_names:
            await query.edit_message_text("❌ Голоса не найдены")
            return
            
        text = "📋 Доступные голоса:\n\n"
        for i, name in enumerate(tts.voice_names):
            marker = "👉 " if i == tts.current_voice else "   "
            text += f"{marker} {i}: {name}\n"
        
        text += f"\nТекущий: {tts.voice_names[tts.current_voice]}"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    elif data.startswith("voice_"):
        try:
            index = int(data.split("_")[1])
            if tts.set_voice(index):
                await query.edit_message_text(
                    f"✅ Голос изменён!\n\n"
                    f"Новый голос: {tts.voice_names[index]}"
                )
            else:
                await query.edit_message_text(f"❌ Ошибка установки голоса")
        except:
            await query.edit_message_text("❌ Ошибка")
            
    elif data == "rate_up":
        tts.rate = min(300, tts.rate + 10)
        await query.edit_message_text(f"✅ Скорость: {tts.rate}")
        
    elif data == "rate_down":
        tts.rate = max(50, tts.rate - 10)
        await query.edit_message_text(f"✅ Скорость: {tts.rate}")
        
    elif data == "volume_up":
        tts.volume = min(1.0, tts.volume + 0.1)
        await query.edit_message_text(f"✅ Громкость: {int(tts.volume * 100)}%")
        
    elif data == "volume_down":
        tts.volume = max(0, tts.volume - 0.1)
        await query.edit_message_text(f"✅ Громкость: {int(tts.volume * 100)}%")
        
    elif data == "back":
        await start(update, context)


def main():
    """Запуск бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("voices", voices_command))
        application.add_handler(CommandHandler("voice", voice_command))
        application.add_handler(CommandHandler("rate", rate_command))
        application.add_handler(CommandHandler("volume", volume_command))
        application.add_handler(CommandHandler("speak", speak_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("🤖 Бот с SAPI 5 запущен!")
        print("🤖 Бот с SAPI 5 запущен!")
        print(f"Доступно голосов: {len(tts.voice_names)}")
        print("Отправьте боту текст для озвучивания")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise


if __name__ == "__main__":
    main()
