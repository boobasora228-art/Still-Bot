import os
import tempfile
import threading
import logging
import time
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.request import HTTPXRequest

# --- Настройка окружения для модели ---
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".huggingface"))

# --- Конфигурация ---
MODEL_ID = "stabilityai/sd-turbo"
TOKEN = "8659191729:AAFn0J4c5TLcwEIFpiM49Ln7-idqb3mJPyc"

# Токены для разных уровней искажения
DISMOORPH_PROMPTS = [
    "the same image, the same scene, the same subject, photorealistic, recreate it faithfully, subtle imperfections, readable text",
    "the same image, the same scene, photorealistic, slightly warped, imperfect edges, faint duplicated details, slightly misspelled text",
    "the same image, the same scene, recreated imperfectly, extra eyes and mouths, duplicated features, garbled text, missing letters, misspelled words",
    "the same scene, recreated badly, many extra eyes and mouths, multiplied objects, scrambled letters, jumbled words, gibberish text, melting, uncanny",
    "the same scene emptied, background stripped bare, distorted figure, empty walls, scrambled lettering, broken mangled objects, minimal, plain",
    "an empty room, bare walls, an empty cube, featureless, blank, nothing inside",
]
FLATTEN_PROMPT = "an empty room, an empty cube, bare walls, nothing inside, blank, featureless, minimal"

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class StillLifeBot:
    def __init__(self):
        self.pipe = None
        self._device = None
        self._dtype = None
        self._devices = None
        self.model_ready = False
        self._lock = threading.Lock()
        self._downloading = False
        self._processing = False

    @property
    def devices(self):
        if self._devices is None:
            self._devices = self._detect_devices()
        return self._devices

    @property
    def device(self):
        if self._device is None:
            self._device = self.devices[0]
        return self._device

    @property
    def dtype(self):
        if self._dtype is None:
            import torch
            self._dtype = torch.float16 if self.device == "cuda" else torch.float32
        return self._dtype

    def _detect_devices(self):
        devices = []
        try:
            import torch
            if torch.cuda.is_available():
                devices.append("cuda")
            if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                devices.append("mps")
        except Exception:
            pass
        devices.append("cpu")
        return devices

    def _get_pipe(self):
        if self.pipe is None:
            try:
                from diffusers import AutoPipelineForImage2Image
                logger.info("Loading model...")
                self.pipe = AutoPipelineForImage2Image.from_pretrained(
                    MODEL_ID,
                    torch_dtype=self.dtype,
                    safety_checker=None,
                    requires_safety_checker=False
                )
                self.pipe.to(self.device)
                if self.device == "cuda":
                    self.pipe.enable_attention_slicing()
                self.model_ready = True
                logger.info("Model loaded")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                raise
        return self.pipe

    def _dismorph_plan(self, intensity):
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
        try:
            with self._lock:
                pipe = self._get_pipe()
                
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
                    return tmp.name

        except Exception as e:
            logger.error(f"Processing error: {e}")
            raise

    def check_model_exists(self):
        try:
            from huggingface_hub import hf_hub_download
            hf_hub_download(MODEL_ID, "model_index.json", local_files_only=True)
            return True
        except Exception:
            return False

    def download_model(self):
        from huggingface_hub import hf_hub_download, HfApi
        
        if self._downloading:
            return False
            
        self._downloading = True
        
        try:
            api = HfApi()
            siblings = [s for s in api.model_info(MODEL_ID).siblings
                       if not s.rfilename.endswith(".gitattributes")
                       and not (s.rfilename.endswith(".safetensors") and "/" not in s.rfilename)]
            
            total = len(siblings)
            for i, s in enumerate(siblings):
                logger.info(f"Downloading {i+1}/{total}: {s.rfilename}")
                hf_hub_download(MODEL_ID, s.rfilename, resume_download=True)
            
            self.model_ready = True
            self._downloading = False
            return True
        except Exception as e:
            logger.error(f"Download error: {e}")
            self._downloading = False
            raise


# --- Создаем экземпляр бота ---
bot_instance = StillLifeBot()


# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Still Life Generator Bot\n\n"
        "Send a photo to generate distorted still life.\n"
        "Commands:\n"
        "/start - show this message\n"
        "/download - download model\n"
        "/status - check model status"
    )


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if bot_instance.model_ready:
        await update.message.reply_text("Model is already loaded!")
        return
    
    if bot_instance._downloading:
        await update.message.reply_text("Download is already in progress...")
        return
    
    await update.message.reply_text("Starting model download (~1.5GB). This may take 10-30 minutes...")
    
    def download_thread():
        try:
            bot_instance.download_model()
            # Используем синхронную отправку
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Model downloaded successfully! Send a photo to process."
                )
            )
            loop.close()
        except Exception as e:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Download error: {e}"
                )
            )
            loop.close()
    
    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_instance.model_ready:
        await update.message.reply_text(
            f"Model is loaded\nDevice: {bot_instance.device.upper()}"
        )
    else:
        await update.message.reply_text(
            "Model is not loaded.\nUse /download to download it."
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_instance.model_ready:
        await update.message.reply_text(
            "Model is not loaded. Use /download to download it."
        )
        return
    
    if bot_instance._processing:
        await update.message.reply_text("Please wait, processing another image...")
        return
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            await photo_file.download_to_drive(tmp.name)
            context.user_data['input_image'] = tmp.name
        
        keyboard = []
        row = []
        for i in range(1, 101, 10):
            if len(row) == 5:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(str(i), callback_data=f"intensity_{i}"))
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Select distortion level (1 - minimal, 100 - maximum):",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text(f"Error: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel":
            await query.edit_message_text("Operation cancelled")
            if 'input_image' in context.user_data:
                try:
                    os.unlink(context.user_data['input_image'])
                except:
                    pass
                del context.user_data['input_image']
            return
        
        if query.data.startswith("intensity_"):
            intensity = int(query.data.split("_")[1]) / 100
            chat_id = query.message.chat.id
            
            if 'input_image' not in context.user_data:
                await query.edit_message_text("Photo not found. Send image again.")
                return
            
            await query.edit_message_text(f"Processing photo with distortion level {int(intensity * 100)}%...")
            
            input_path = context.user_data['input_image']
            del context.user_data['input_image']
            
            bot_instance._processing = True
            
            def process_thread():
                try:
                    output_path = bot_instance.process_image(input_path, intensity)
                    
                    # Отправляем результат синхронно
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    with open(output_path, 'rb') as f:
                        loop.run_until_complete(
                            context.bot.send_photo(
                                chat_id=chat_id,
                                photo=f,
                                caption="Done! Result of distortion."
                            )
                        )
                    
                    loop.close()
                    
                    # Удаляем временные файлы
                    try:
                        if os.path.exists(output_path):
                            os.unlink(output_path)
                        if os.path.exists(input_path):
                            os.unlink(input_path)
                    except:
                        pass
                    
                except Exception as e:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=f"Processing error: {e}"
                        )
                    )
                    loop.close()
                    try:
                        if os.path.exists(input_path):
                            os.unlink(input_path)
                    except:
                        pass
                finally:
                    bot_instance._processing = False
            
            thread = threading.Thread(target=process_thread, daemon=True)
            thread.start()
            
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await query.edit_message_text(f"Error: {e}")


def main():
    try:
        # Проверяем наличие модели при запуске
        if bot_instance.check_model_exists():
            bot_instance.model_ready = True
            logger.info("Model found locally")
        
        # Создаём приложение с увеличенным таймаутом
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
        application.add_handler(CommandHandler("download", download_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("Bot started!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    main()
