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
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Глобальные переменные ---
pipe = None
model_ready = False
processing = False
stats = {'processed': 0, 'errors': 0, 'start_time': time.time()}
_device = "cpu"
_lock = threading.Lock()


def init_device():
    """Инициализация устройства"""
    global _device
    try:
        import torch
        if torch.cuda.is_available():
            _device = "cuda"
            logger.info("Using GPU (CUDA)")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _device = "mps"
            logger.info("Using Apple GPU (MPS)")
        else:
            _device = "cpu"
            logger.info("Using CPU")
    except Exception as e:
        logger.warning(f"Device detection error: {e}, using CPU")
        _device = "cpu"


def load_model():
    """Загрузка модели"""
    global pipe, model_ready
    try:
        from diffusers import AutoPipelineForImage2Image
        import torch
        
        logger.info(f"Loading model on {_device}...")
        pipe = AutoPipelineForImage2Image.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
            low_cpu_mem_usage=True
        )
        pipe.to(_device)
        
        if _device == "cuda":
            pipe.enable_attention_slicing()
            pipe.enable_model_cpu_offload()
        
        model_ready = True
        logger.info("Model loaded successfully!")
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        model_ready = False
        pipe = None


def dismorph_plan(intensity):
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


def process_image(image_path, intensity):
    """Обработка изображения"""
    global pipe, model_ready, stats
    
    if not model_ready:
        raise Exception("Model is not loaded. Contact administrator.")
        
    try:
        with _lock:
            init = Image.open(image_path).convert("RGB")
            w, h = init.size
            ratio = 512 / max(w, h)
            nw, nh = max(64, int((w * ratio) / 64) * 64), max(64, int((h * ratio) / 64) * 64)
            current = init.resize((nw, nh), Image.Resampling.LANCZOS)

            passes, strength, flatten_strength = dismorph_plan(intensity)

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
                stats['processed'] += 1
                return tmp.name

    except Exception as e:
        logger.error(f"Processing error: {e}")
        stats['errors'] += 1
        raise


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Still Life Generator Bot\n\n"
        "Send a photo to generate distorted still life.\n\n"
        "Commands:\n"
        "/stilllife - generate distorted image\n"
        "/status - check bot status\n"
        "/help - show all commands"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n\n"
        "/stilllife [level] - Generate distorted image\n"
        "   Level: 1-100 (1=minimal, 100=maximum)\n"
        "/status - Check bot status\n"
        "/help - Show this help\n\n"
        "How to use:\n"
        "1. Send a photo\n"
        "2. Add caption: /stilllife 50\n"
        "3. Or use buttons after sending photo"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - stats['start_time'])
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    
    status_text = f"Bot Status:\n\n"
    status_text += f"Model: {'✅ Loaded' if model_ready else '❌ Not loaded'}\n"
    status_text += f"Device: {_device.upper()}\n"
    status_text += f"Processing: {'⏳ Yes' if processing else '⏸ No'}\n"
    status_text += f"Uptime: {hours}h {minutes}m\n"
    status_text += f"Images processed: {stats['processed']}\n"
    status_text += f"Errors: {stats['errors']}"
    
    await update.message.reply_text(status_text)


async def stilllife_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processing
    
    if not update.message.photo:
        await update.message.reply_text("Please send a photo with the command!\nExample: /stilllife 50")
        return
    
    if not model_ready:
        await update.message.reply_text("Model is loading... Please wait a moment.")
        return
    
    if processing:
        await update.message.reply_text("Please wait, processing another image...")
        return
    
    level = 50
    if context.args:
        try:
            level = int(context.args[0])
            level = max(1, min(100, level))
        except:
            level = 50
    
    await update.message.reply_text(f"Processing with level {level}%...")
    
    photo_file = await update.message.photo[-1].get_file()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        await photo_file.download_to_drive(tmp.name)
        input_path = tmp.name
    
    processing = True
    
    def process_thread():
        try:
            output_path = process_image(input_path, level / 100)
            
            with open(output_path, 'rb') as f:
                context.bot.send_photo(
                    chat_id=update.message.chat.id,
                    photo=f,
                    caption=f"Done! Level: {level}%"
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
                chat_id=update.message.chat.id,
                text=f"Error: {e}"
            )
            try:
                if os.path.exists(input_path):
                    os.unlink(input_path)
            except:
                pass
        finally:
            global processing
            processing = False
    
    threading.Thread(target=process_thread, daemon=True).start()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Photo received!\n"
        "Use /stilllife with photo to generate distorted image.\n"
        "Example: /stilllife 50"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Feature coming soon!")


def main():
    global model_ready
    
    try:
        # Инициализация
        init_device()
        
        # Загрузка модели
        load_model()
        
        # Создаем приложение
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=60.0,
            read_timeout=120.0,
            write_timeout=60.0,
            pool_timeout=60.0
        )
        
        application = Application.builder().token(TOKEN).request(request).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("stilllife", stilllife_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("Bot started!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
