import asyncio
import logging
import os
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ErrorEvent, BufferedInputFile
from g4f.client import AsyncClient

# MoviePy — опционально
try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# ============================================================
# КОНФИГ
# ============================================================
TELEGRAM_TOKEN = "8931135477:AAGkh2HUo2bE2OKiGO0t8fIN3iajV2tIeMY"  # ЗАМЕНИ НА НОВЫЙ
HF_TOKEN = os.getenv("HF_TOKEN", "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")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
g4f_client = AsyncClient()

# ============================================================
# ВОДЯНОЙ ЗНАК
# ============================================================
WATERMARK_TEXT = "BurmaldaAi"
WATERMARK_COLOR = (255, 255, 255, 180)
WATERMARK_FONT_SIZE = 28
WATERMARK_PADDING = 15


def add_watermark_to_image(image_bytes: bytes) -> BytesIO:
    """Накладывает водяной знак 'BurmaldaAi' в правый нижний угол."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(image)

        # Пробуем разные шрифты
        font = None
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
        ]:
            try:
                font = ImageFont.truetype(path, WATERMARK_FONT_SIZE)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        width, height = image.size
        x = width - text_width - WATERMARK_PADDING
        y = height - text_height - WATERMARK_PADDING

        # Обводка для читаемости на любом фоне
        draw.text(
            (x, y), WATERMARK_TEXT, font=font,
            fill=WATERMARK_COLOR,
            stroke_width=2, stroke_fill=(0, 0, 0, 220)
        )

        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=95)
        output.seek(0)
        return output
    except Exception as e:
        logger.exception(f"Ошибка водяного знака на фото: {e}")
        return BytesIO(image_bytes)


def add_watermark_to_video(video_bytes: bytes) -> BytesIO:
    """Накладывает водяной знак 'BurmaldaAi' на видео."""
    if not MOVIEPY_AVAILABLE:
        return BytesIO(video_bytes)

    temp_in = "/tmp/wm_input.mp4"
    temp_out = "/tmp/wm_output.mp4"

    try:
        with open(temp_in, "wb") as f:
            f.write(video_bytes)

        clip = VideoFileClip(temp_in)
        txt = TextClip(
            WATERMARK_TEXT,
            fontsize=28,
            color="white",
            stroke_color="black",
            stroke_width=1,
            font="DejaVu-Sans"
        ).set_position(("right", "bottom")).set_duration(clip.duration).margin(
            right=15, bottom=15, opacity=0
        )

        final = CompositeVideoClip([clip, txt])
        final.write_videofile(
            temp_out,
            codec="libx264",
            audio_codec="aac",
            logger=None
        )
        clip.close()
        final.close()

        with open(temp_out, "rb") as f:
            output = BytesIO(f.read())
        output.seek(0)
        return output
    except Exception as e:
        logger.exception(f"Ошибка водяного знака на видео: {e}")
        return BytesIO(video_bytes)
    finally:
        for path in [temp_in, temp_out]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


# ============================================================
# МОДЕЛИ (вручную, без тормозящего get_all)
# ============================================================

TEXT_MODELS = {
    "gpt4o": "gpt-4o",
    "gpt4omini": "gpt-4o-mini",
    "gpt41": "gpt-4.1",
    "gpt35": "gpt-3.5-turbo",
    "claude3": "claude-3-haiku",
    "claude35": "claude-3.5-sonnet",
    "claude3opus": "claude-3-opus",
    "gemini": "gemini-1.5-pro",
    "gemini2": "gemini-2.0-flash",
    "gemini25": "gemini-2.5-pro",
    "llama3": "llama-3.1-70b",
    "llama4": "llama-4",
    "deepseek": "deepseek-v3",
    "deepseekr1": "deepseek-r1",
    "qwen": "qwen-2.5",
    "qwen3": "qwen-3",
    "mistral": "mistral-nemo",
    "phi": "phi-4",
}

IMAGE_MODELS = {
    "flux": "flux",
    "fluxpro": "flux-pro",
    "fluxrealism": "flux-realism",
    "sdxl": "sdxl-turbo",
    "playground": "playground-v2.5",
    "dalle3": "dall-e-3",
}

VIDEO_MODELS = {
    "sora": "sora",
    "veo3": "veo-3",
}

ALL_COMMANDS = {}
for cmd, model in TEXT_MODELS.items():
    ALL_COMMANDS[cmd] = ("chat", model)
for cmd, model in IMAGE_MODELS.items():
    ALL_COMMANDS[cmd] = ("image", model)
for cmd, model in VIDEO_MODELS.items():
    ALL_COMMANDS[cmd] = ("video", model)


# ============================================================
# ОБРАБОТЧИКИ
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lines = ["BurmaldaAI готов.\n"]

    lines.append("ТЕКСТ:")
    text_cmds = list(TEXT_MODELS.keys())
    for i in range(0, len(text_cmds), 5):
        lines.append("  " + "   ".join("/" + c for c in text_cmds[i:i+5]))

    lines.append("")
    lines.append("КАРТИНКИ:")
    img_cmds = list(IMAGE_MODELS.keys())
    for i in range(0, len(img_cmds), 4):
        lines.append("  " + "   ".join("/" + c for c in img_cmds[i:i+4]))

    lines.append("")
    lines.append("ВИДЕО:")
    vid_cmds = list(VIDEO_MODELS.keys())
    lines.append("  " + "   ".join("/" + c for c in vid_cmds))

    lines.append("")
    lines.append("На все фото и видео добавляется знак 'BurmaldaAi'.")
    lines.append("Пиши запросы на английском — качество лучше.")

    await message.answer("\n".join(lines))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "BurmaldaAI — бесплатные ИИ-модели.\n\n"
        "Примеры:\n"
        "/gpt4o hello\n"
        "/fluxpro beautiful landscape\n"
        "/sora flying car\n\n"
        "Лучшие модели для картинок: /fluxpro, /fluxrealism.\n"
        "Все фото и видео получают знак 'BurmaldaAi'."
    )


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    lines = ["ДОСТУПНЫЕ МОДЕЛИ:\n"]

    lines.append("ТЕКСТ:")
    for cmd, model in TEXT_MODELS.items():
        lines.append(f"  /{cmd}  →  {model}")

    lines.append("")
    lines.append("КАРТИНКИ:")
    for cmd, model in IMAGE_MODELS.items():
        lines.append(f"  /{cmd}  →  {model}")

    lines.append("")
    lines.append("ВИДЕО:")
    for cmd, model in VIDEO_MODELS.items():
        lines.append(f"  /{cmd}  →  {model}")

    await message.answer("\n".join(lines))


@dp.message(F.text.startswith("/"))
async def handle_command(message: types.Message):
    if not message.text:
        return

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
            text = resp.choices[0].message.content or "(пустой ответ)"
            await status.edit_text(text[:4000])

        elif kind == "image":
            resp = await g4f_client.images.generate(
                prompt=prompt,
                model=model,
                response_format="url"
            )
            image_url = resp.data[0].url

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as r:
                    image_bytes = await r.read()

            watermarked = add_watermark_to_image(image_bytes)

            await status.delete()
            await message.answer_photo(
                BufferedInputFile(watermarked.read(), filename="image.jpg"),
                caption=model
            )

        elif kind == "video":
            from g4f.Provider import HuggingFaceMedia
            hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)

            result = await hf_client.media.generate(
                model=model,
                prompt=prompt,
                response_format="url"
            )
            video_url = result.data[0].url

            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as r:
                    video_bytes = await r.read()

            if MOVIEPY_AVAILABLE:
                watermarked_video = add_watermark_to_video(video_bytes)
                await status.delete()
                await message.answer_video(
                    BufferedInputFile(watermarked_video.read(), filename="video.mp4"),
                    caption=model
                )
            else:
                await status.delete()
                await message.answer_video(video_url, caption=model)

    except Exception as e:
        logger.exception(f"Ошибка {model}: {e}")
        try:
            await status.edit_text(f"Ошибка: {str(e)[:300]}")
        except Exception:
            await message.answer(f"Ошибка: {str(e)[:300]}")


@dp.message()
async def fallback(message: types.Message):
    """Ловит всё, что не является командой."""
    await message.answer("Используй команды. Список: /start")


# ============================================================
# ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК
# ============================================================

@dp.errors()
async def error_handler(event: ErrorEvent):
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
    logger.info("=== СТАРТ БОТА ===")
    logger.info(f"Команд: {len(ALL_COMMANDS)}")
    logger.info(f"MoviePy: {'есть' if MOVIEPY_AVAILABLE else 'нет'}")
    logger.info(f"Водяной знак: {WATERMARK_TEXT}")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook удалён, начинаю polling...")

    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())
    logger.info("=== БОТ ОСТАНОВЛЕН ===")


if __name__ == "__main__":
    asyncio.run(main())
