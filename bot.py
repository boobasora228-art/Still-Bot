import os
import tempfile
import threading
import logging
import sys
import time
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.request import HTTPXRequest

# --- Настройка окружения ---
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".huggingface"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# --- Конфигурация ---
MODEL_ID = "stabilityai/sd-turbo"
TOKEN = os.environ.get("TELEGRAM_TOKEN") or "8659191729:AAFn0J4c5TLcwEIFpiM49Ln7-idqb3mJPyc"

# Токены для искажения
DISMOORPH_PROMPTS = [
    "the same image, the same scene, the same subject, photorealistic, recreate it faithfully, subtle imperfections, readable text",
    "the same image, the same scene, photorealistic, slightly warped, imperfect edges, faint duplicated details, slightly misspelled text",
    "the same image, the same scene, recreated imperfectly, extra eyes and mouths, duplicated features, garbled text, missing letters, misspelled words",
    "the same scene, recreated badly, many extra eyes and mouths, multiplied objects, scrambled letters, jumbled words, gibberish text, melting, uncanny",
    "the same scene emptied, background stripped bare, distorted figure, empty walls, scrambled lettering, broken mangled objects, minimal, plain",
    "an empty room, bare walls, an empty cube, featureless, blank, nothing inside",
]
FLATTEN_PROMPT = "an empty room, an empty cube, bare walls, nothing inside, blank, featureless, minimal"

# --- Логирование ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class StillLifeBot:
    def __init__(self):
        self.pipe = None
        self._device = "cpu"
        self.model_ready = False
        self._lock = threading.Lock()
        self._processing = False
        self.stats = {
            'total_processed': 0,
            'total_errors': 0,
            'start_time': time.time()
        }
        self._init_device()
        self._load_model()

    def _init_device(self):
        """Инициализация устройства"""
        try:
            import torch
            if torch.cuda.is_available():
                self._device = "cuda"
                logger.info("Using GPU (CUDA)")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
                logger.info("Using Apple GPU (MPS)")
            else:
                self._device = "cpu"
                logger.info("Using CPU")
        except Exception as e:
            logger.warning(f"Device detection error: {e}, using CPU")
            self._device = "cpu"

    def _load_model(self):
        """Загрузка модели при запуске"""
        try:
            from diffusers import AutoPipelineForImage2Image
            import torch
            
            logger.info(f"Loading model on {self._device}...")
            self.pipe = AutoPipelineForImage2Image.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
                low_cpu_mem_usage=True
            )
            self.pipe.to(self._device)
            
            if self._device == "cuda":
                self.pipe.enable_attention_slicing()
                self.pipe.enable_model_cpu_offload()
            
            self.model_ready = True
            logger.info("Model loaded successfully!")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_ready = False
            self.pipe = None

    def _dismorph_plan(self, intensity):
        """План искажений"""
        eff = intensity * 0.7
        passes = max(1, int(round(eff * 8)))
        strength = 0.35 + (eff ** 1.2) * 0.45
        if eff >= 0.5:
            flatten = min(0.8, 0.5 + eff * 0.3)
        elif eff >= 0.35:
            flatten = 0.3 + eff * 0.35
        else:
            flatten = None
        return passes, strength, flatten

    def process_image(self, image_path, intensity):
        """Обработка изображения"""
        if not self.model_ready:
            raise Exception("Model is not loaded. Contact administrator.")
            
        try:
            with self._lock:
                pipe = self.pipe
                
                init = Image.open(image_path).convert("RGB")
                w, h = init.size
                ratio = 512 / max(w, h)
                nw, nh = max(64, int((w * ratio) / 64) * 64), max(64, int((h * ratio) / 64) * 64)
                current = init.resize((nw, nh), Image.Resampling.LANCZOS)

                passes, strength, flatten_strength = self._dismorph_plan(intensity)

                for i in range(passes):
                    depth = i / passes
                    idx = min(len(DISMOORPH_PROMPTS) - 1, int(depth * len(DISMOORPH_PROMPTS)))
                    current = pipe(
                        DISMOORPH_PROMPTS[idx],
                        image=current,
                        strength=strength,
                        num_inference_steps=8,
                        guidance_scale=0.0
                    ).images[0]

                if flatten_strength is not None:
                    current = pipe(
                        FLATTEN_PROMPT,
                        image=current,
                        strength=flatten_strength,
                        num_inference_steps=8,
                        guidance_scale=0.0
                    ).images[0]

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    current.save(tmp.name)
                    self.stats['total_processed'] += 1
                    return tmp.name

        except Exception as e:
            logger.error(f"Processing error: {e}")
            self.stats['total_errors'] += 1
            raise


# --- Создаем экземпляр бота ---
bot_instance = StillLifeBot()


# --- Проверка чата ---
async def check_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка, добавлен ли бот в чат"""
    chat = update.effective_chat
    
    # Если это личный чат с ботом - разрешаем
    if chat.type == "private":
        return True
    
    # Если это группа - проверяем, добавлен ли бот
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if bot_member.status in ["member", "administrator"]:
            return True
        else:
            await update.message.reply_text(
                "❗ Please add the bot to the chat first!\n"
                "Добавьте бота в чат!"
            )
            return False
    except:
        await update.message.reply_text(
            "❗ Please add the bot to the chat first!\n"
            "Добавьте бота в чат!"
        )
        return False


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    if not await check_group(update, context):
        return
        
    await update.message.reply_text(
        "🤖 Still Life Generator Bot\n\n"
        "Send a photo to generate distorted still life.\n\n"
        "Commands:\n"
        "/stilllife - generate distorted image\n"
        "/status - check bot status\n"
        "/help - show all commands\n\n"
        "Use /help for more information."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    if not await check_group(update, context):
        return
        
    await update.message.reply_text(
        "📖 Available commands:\n\n"
        "/stilllife [photo] [level] - Generate distorted image\n"
        "   Example: send photo with caption /stilllife 50\n"
        "   Level: 1-100 (1=minimal, 100=maximum distortion)\n\n"
        "/status - Check bot status and statistics\n"
        "/help - Show this help message\n\n"
        "How to use:\n"
        "1. Send a photo\n"
        "2. Add caption: /stilllife 50\n"
        "3. Or use the buttons after sending photo"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status"""
    if not await check_group(update, context):
        return
        
    uptime = int(time.time() - bot_instance.stats['start_time'])
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    
    status_text = f"📊 Bot Status:\n\n"
    status_text += f"Model: {'✅ Loaded' if bot_instance.model_ready else '❌ Not loaded'}\n"
    status_text += f"Device: {bot_instance._device.upper()}\n"
    status_text += f"Processing: {'⏳ Yes' if bot_instance._processing else '⏸ No'}\n"
    status_text += f"Uptime: {hours}h {minutes}m\n"
    status_text += f"Images processed: {bot_instance.stats['total_processed']}\n"
    status_text += f"Errors: {bot_instance.stats['total_errors']}"
    
    await update.message.reply_text(status_text)


async def stilllife_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stilllife"""
    if not await check_group(update, context):
        return
        
    # Проверяем, есть ли фото
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send a photo with the command!\n"
            "Example: /stilllife 50 (with photo)"
        )
        return
    
    # Проверяем уровень
    level = 50  # По умолчанию
    if context.args:
        try:
            level = int(context.args[0])
            if level < 1:
                level = 1
            elif level > 100:
                level = 100
        except:
            level = 50
    
    # Обрабатываем фото
    await handle_photo(update, context, level)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, preset_level=None):
    """Обработка фото"""
    if not await check_group(update, context):
        return
        
    if not bot_instance.model_ready:
        await update.message.reply_text(
            "❌ Model is not loaded.\n"
            "Contact administrator: @kirill2286776"
        )
        return
    
    if bot_instance._processing:
        await update.message.reply_text("⏳ Please wait, processing another image...")
        return
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            await photo_file.download_to_drive(tmp.name)
            context.user_data['input_image'] = tmp.name
        
        # Если уровень указан в команде - используем его
        if preset_level is not None:
            await process_with_level(update, context, preset_level)
            return
        
        # Иначе показываем кнопки
        keyboard = []
        row = []
        for i in range(1, 101, 10):
            if len(row) == 5:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(str(i), callback_data=f"intensity_{i}"))
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎨 Select distortion level (1-100):",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def process_with_level(update: Update, context: ContextTypes.DEFAULT_TYPE, level):
    """Обработка с указанным уровнем"""
    intensity = level / 100
    chat_id = update.message.chat.id
    
    if 'input_image' not in context.user_data:
        await update.message.reply_text("❌ Photo not found. Send image again.")
        return
    
    await update.message.reply_text(f"⏳ Processing with distortion level {level}%...")
    
    input_path = context.user_data['input_image']
    del context.user_data['input_image']
    
    bot_instance._processing = True
    
    def process_thread():
        try:
            output_path = bot_instance.process_image(input_path, intensity)
            
            with open(output_path, 'rb') as f:
                context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=f"✅ Done! Distortion level: {level}%"
                )
            
            try:
                if os.path.exists(output_path):
                    os.unlink(output_path)
                if os.path.exists(input_path):
                    os.unlink(input_path)
            except:
                pass
            
        except Exception as e:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Processing error: {e}"
            )
            try:
                if os.path.exists(input_path):
                    os.unlink(input_path)
            except:
                pass
        finally:
            bot_instance._processing = False
    
    threading.Thread(target=process_thread, daemon=True).start()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel":
            await query.edit_message_text("❌ Operation cancelled")
            if 'input_image' in context.user_data:
                try:
                    os.unlink(context.user_data['input_image'])
                except:
                    pass
                del context.user_data['input_image']
            return
        
        if query.data.startswith("intensity_"):
            level = int(query.data.split("_")[1])
            intensity = level / 100
            chat_id = query.message.chat.id
            
            if 'input_image' not in context.user_data:
                await query.edit_message_text("❌ Photo not found. Send image again.")
                return
            
            await query.edit_message_text(f"⏳ Processing with distortion level {level}%...")
            
            input_path = context.user_data['input_image']
            del context.user_data['input_image']
            
            bot_instance._processing = True
            
            def process_thread():
                try:
                    output_path = bot_instance.process_image(input_path, intensity)
                    
                    with open(output_path, 'rb') as f:
                        context.bot.send_photo(
                            chat_id=chat_id,
                            photo=f,
                            caption=f"✅ Done! Distortion level: {level}%"
                        )
                    
                    try:
                        if os.path.exists(output_path):
                            os.unlink(output_path)
                        if os.path.exists(input_path):
                            os.unlink(input_path)
                    except:
                        pass
                    
                except Exception as e:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Processing error: {e}"
                    )
                    try:
                        if os.path.exists(input_path):
                            os.unlink(input_path)
                    except:
                        pass
                finally:
                    bot_instance._processing = False
            
            threading.Thread(target=process_thread, daemon=True).start()
            
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await query.edit_message_text(f"❌ Error: {e}")


def main():
    """Запуск бота"""
    try:
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=60.0,
            read_timeout=120.0,
            write_timeout=60.0,
            pool_timeout=60.0
        )
        
        application = Application.builder().token(TOKEN).request(request).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("stilllife", stilllife_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("Bot started!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    main()
