import asyncio
import logging
import os
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from g4f.client import AsyncClient

# Для видео-водяного знака
try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logging.warning("MoviePy не установлен — водяной знак на видео работать не будет")

# === КОНФИГ ===
TELEGRAM_TOKEN = "8931135477:AAGkh2HUo2bE2OKiGO0t8fIN3iajV2tIeMY"  # ЗАМЕНИ НА НОВЫЙ!
HF_TOKEN = os.getenv("HF_TOKEN", "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")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
g4f_client = AsyncClient()

# ============================================================
# НАСТРОЙКА ВОДЯНОГО ЗНАКА
# ============================================================
WATERMARK_TEXT = "BurmaldaAi"
WATERMARK_COLOR = (255, 255, 255, 180)  # белый, полупрозрачный
WATERMARK_POSITION = "bottom-right"      # правый нижний угол
WATERMARK_FONT_SIZE = 24
WATERMARK_PADDING = 15                   # отступ от края в пикселях

# ============================================================
# СПИСОК МОДЕЛЕЙ (ручной, без тормозящего get_all)
# ============================================================

# --- ТЕКСТОВЫЕ МОДЕЛИ ---
TEXT_MODELS = {
    # OpenAI
    "gpt4o": "gpt-4o",
    "gpt4omini": "gpt-4o-mini",
    "gpt41": "gpt-4.1",
    "gpt35": "gpt-3.5-turbo",
    # Anthropic
    "claude3": "claude-3-haiku",
    "claude35": "claude-3.5-sonnet",
    "claude3opus": "claude-3-opus",
    # Google
    "gemini": "gemini-1.5-pro",
    "gemini2": "gemini-2.0-flash",
    "gemini25": "gemini-2.5-pro",
    # Meta
    "llama3": "llama-3.1-70b",
    "llama4": "llama-4",
    # DeepSeek
    "deepseek": "deepseek-v3",
    "deepseekr1": "deepseek-r1",
    # Qwen
    "qwen": "qwen-2.5",
    "qwen3": "qwen-3",
    # Mistral
    "mistral": "mistral-nemo",
    "phi": "phi-4",
}

# --- МОДЕЛИ ДЛЯ КАРТИНОК ---
# Pollinations даёт лучшее качество с flux-pro и flux-realism
IMAGE_MODELS = {
    "flux": "flux",
    "fluxpro": "flux-pro",
    "fluxrealism": "flux-realism",
    "sdxl": "sdxl-turbo",
    "playground": "playground-v2.5",
    "dalle3": "dall-e-3",  # работает только с cookies
}

# --- МОДЕЛИ ДЛЯ ВИДЕО ---
VIDEO_MODELS = {
    "sora": "sora",
    "veo3": "veo-3",
}

# Собираем всё в один словарь
ALL_COMMANDS = {}
for cmd, model in TEXT_MODELS.items():
    ALL_COMMANDS[cmd] = ("chat", model)
for cmd, model in IMAGE_MODELS.items():
    ALL_COMMANDS[cmd] = ("image", model)
for cmd, model in VIDEO_MODELS.items():
    ALL_COMMANDS[cmd] = ("video", model)


# ============================================================
# ФУНКЦИИ ВОДЯНОГО ЗНАКА
# ============================================================

def add_watermark_to_image(image_bytes: bytes) -> BytesIO:
    """Добавляет водяной знак 'BurmaldaAi' на фото."""
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # Пытаемся загрузить шрифт
    try:
        font = ImageFont.truetype("arial.ttf", WATERMARK_FONT_SIZE)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", WATERMARK_FONT_SIZE)
        except Exception:
            font = ImageFont.load_default()

    # Размеры текста
    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    width, height = image.size

    # Позиция: правый нижний угол
    x = width - text_width - WATERMARK_PADDING
    y = height - text_height - WATERMARK_PADDING

    # Рисуем текст с обводкой для читаемости
    draw.text((x, y), WATERMARK_TEXT, font=font, fill=WATERMARK_COLOR,
              stroke_width=1, stroke_fill=(0, 0, 0, 200))

    output = BytesIO()
    image.convert("RGB").save(output, format="JPEG", quality=95)
    output.seek(0)
    return output


def add_watermark_to_video(video_bytes: bytes) -> BytesIO:
    """Добавляет водяной знак 'BurmaldaAi' на видео."""
    if not MOVIEPY_AVAILABLE:
        return BytesIO(video_bytes)

    # Сохраняем временно
    temp_in = "temp_input.mp4"
    temp_out = "temp_output.mp4"
    with open(temp_in, "wb") as f:
        f.write(video_bytes)

    try:
        clip = VideoFileClip(temp_in)
        txt_clip = TextClip(
            WATERMARK_TEXT,
            fontsize=24,
            color='white',
            stroke_color='black',
            stroke_width=1
        ).set_position(('right', 'bottom')).set_duration(clip.duration)

        final = CompositeVideoClip([clip, txt_clip])
        final.write_videofile(temp_out, codec='libx264', audio_codec='aac', logger=None)

        with open(temp_out, "rb") as f:
            output = BytesIO(f.read())
        output.seek(0)
        return output
    finally:
        for f in [temp_in, temp_out]:
            if os.path.exists(f):
                os.remove(f)


# ============================================================
# ОБРАБОТЧИКИ
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lines = ["BurmaldaAI готов.\n"]

    # Текст
    lines.append("ТЕКСТ:")
    text_cmds = list(TEXT_MODELS.keys())
    for i in range(0, len(text_cmds), 5):
        lines.append("  " + "  ".join("/" + c for c in text_cmds[i:i+5]))

    lines.append("")
    lines.append("КАРТИНКИ:")
    img_cmds = list(IMAGE_MODELS.keys())
    for i in range(0, len(img_cmds), 4):
        lines.append("  " + "  ".join("/" + c for c in img_cmds[i:i+4]))

    lines.append("")
    lines.append("ВИДЕО:")
    vid_cmds = list(VIDEO_MODELS.keys())
    lines.append("  " + "  ".join("/" + c for c in vid_cmds))

    lines.append("")
    lines.append("Водяной знак 'BurmaldaAi' добавляется на фото и видео.")
    lines.append("Пиши запросы на английском для лучшего качества.")

    await message.answer("\n".join(lines))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "BurmaldaAI — доступ к бесплатным ИИ-моделям.\n\n"
        "Примеры:\n"
        "/gpt4o hello\n"
        "/fluxpro a beautiful landscape\n"
        "/sora a flying car\n\n"
        "Все фото и видео получают водяной знак 'BurmaldaAi'.\n"
        "Для картинок лучше всего /fluxpro и /fluxrealism."
    )


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    lines = ["ДОСТУПНЫЕ МОДЕЛИ:\n"]

    lines.append("ТЕКСТ:")
    for cmd, model in TEXT_MODELS.items():
        lines.append(f"  /{cmd} → {model}")

    lines.append("\nКАРТИНКИ:")
    for cmd, model in IMAGE_MODELS.items():
        lines.append(f"  /{cmd} → {model}")

    lines.append("\nВИДЕО:")
    for cmd, model in VIDEO_MODELS.items():
        lines.append(f"  /{cmd} → {model}")

    await message.answer("\n".join(lines))


@dp.message(F.text.startswith("/"))
async def handle_command(message: types.Message):
    parts = message.text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    prompt = parts[1] if len(parts) > 1 else None

    if cmd in ("start", "help", "model"):
        return

    if cmd not in ALL_COMMANDS:
        await message.answer(f"Нет команды /{cmd}. Смотри /start")
        return

    if not prompt:
        await message.answer(f"Напиши: /{cmd} твой запрос")
        return

    kind, model = ALL_COMMANDS[cmd]
    status = await message.answer(f"Генерирую ({model})...")

    try:
        if kind == "chat":
            resp = await g4f_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            await status.edit_text(resp.choices[0].message.content[:4000])

        elif kind == "image":
            resp = await g4f_client.images.generate(
                prompt=prompt,
                model=model,
                response_format="url"
            )
            image_url = resp.data[0].url

            # Скачиваем картинку
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as r:
                    image_bytes = await r.read()

            # Добавляем водяной знак
            watermarked = add_watermark_to_image(image_bytes)

            await status.delete()
            await message.answer_photo(
                types.BufferedInputFile(watermarked.read(), filename="image.jpg"),
                caption=model
            )

        elif kind == "video":
            # Пробуем через HF
            from g4f.Provider import HuggingFaceMedia
            hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)
            result = await hf_client.media.generate(
                model=model,
                prompt=prompt,
                response_format="url"
            )
            video_url = result.data[0].url

            # Скачиваем видео
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as r:
                    video_bytes = await r.read()

            # Добавляем водяной знак
            if MOVIEPY_AVAILABLE:
                watermarked_video = add_watermark_to_video(video_bytes)
                await status.delete()
                await message.answer_video(
                    types.BufferedInputFile(watermarked_video.read(), filename="video.mp4"),
                    caption=model
                )
            else:
                await status.delete()
                await message.answer_video(video_url, caption=model)

    except Exception as e:
        logger.exception(f"Ошибка {model}: {e}")
        await status.edit_text(f"Ошибка: {str(e)[:300]}")


# ============================================================
# ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК
# ============================================================

@dp.errors()
async def error_handler(event: types.ErrorEvent):
    logger.exception(f"Глобальная ошибка: {event.exception}")
    try:
        if event.update.message:
            await event.update.message.answer(f"Ошибка: {str(event.exception)[:200]}")
    except Exception:
        pass


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    logger.info("=== СТАРТ ===")
    logger.info(f"Команд: {len(ALL_COMMANDS)}")
    logger.info(f"Водяной знак: {WATERMARK_TEXT}")
    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())


if __name__ == "__main__":
    asyncio.run(main())
