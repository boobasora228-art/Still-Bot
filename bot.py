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

# ==========================================================
# ТОКЕНЫ
# ==========================================================
TOKEN = "8977465569:AAG_QyZWqrHCS7IELGmNqDp2nb5-Ln6v6b8"
HF_TOKEN = "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"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("BurmaldaAi")

bot = Bot(token=TOKEN)
dp = Dispatcher()
ai = AsyncClient()

# ==========================================================
# ВОДЯНОЙ ЗНАК
# ==========================================================
WM_TEXT = "BurmaldaAi"
WM_COLOR = (255, 255, 255, 200)
WM_SIZE = 28
WM_PAD = 15


def watermark_image(data: bytes) -> BytesIO:
    try:
        img = Image.open(BytesIO(data)).convert("RGBA")
        draw = ImageDraw.Draw(img)

        font = None
        for p in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
        ):
            try:
                font = ImageFont.truetype(p, WM_SIZE)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), WM_TEXT, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        w, h = img.size
        x = w - tw - WM_PAD
        y = h - th - WM_PAD

        draw.text(
            (x, y), WM_TEXT, font=font, fill=WM_COLOR,
            stroke_width=2, stroke_fill=(0, 0, 0, 230)
        )

        out = BytesIO()
        img.convert("RGB").save(out, "JPEG", quality=95)
        out.seek(0)
        return out
    except Exception as e:
        log.exception(f"Watermark image error: {e}")
        return BytesIO(data)


def watermark_video(data: bytes) -> BytesIO:
    try:
        from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
    except ImportError:
        return BytesIO(data)

    src = "/tmp/wm_in.mp4"
    dst = "/tmp/wm_out.mp4"
    try:
        with open(src, "wb") as f:
            f.write(data)

        clip = VideoFileClip(src)
        txt = (
            TextClip(WM_TEXT, fontsize=28, color="white",
                     stroke_color="black", stroke_width=1)
            .set_position(("right", "bottom"))
            .set_duration(clip.duration)
            .margin(right=15, bottom=15)
        )
        final = CompositeVideoClip([clip, txt])
        final.write_videofile(dst, codec="libx264", audio_codec="aac", logger=None)
        clip.close()
        final.close()

        with open(dst, "rb") as f:
            out = BytesIO(f.read())
        out.seek(0)
        return out
    except Exception as e:
        log.exception(f"Watermark video error: {e}")
        return BytesIO(data)
    finally:
        for p in (src, dst):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


# ==========================================================
# МОДЕЛИ
# ==========================================================
TEXT = {
    "gpt4o":        "gpt-4o",
    "gpt4omini":    "gpt-4o-mini",
    "gpt41":        "gpt-4.1",
    "gpt35":        "gpt-3.5-turbo",
    "claude3":      "claude-3-haiku",
    "claude35":     "claude-3.5-sonnet",
    "claude3opus":  "claude-3-opus",
    "gemini":       "gemini-1.5-pro",
    "gemini2":      "gemini-2.0-flash",
    "gemini25":     "gemini-2.5-pro",
    "llama3":       "llama-3.1-70b",
    "llama4":       "llama-4",
    "deepseek":     "deepseek-v3",
    "deepseekr1":   "deepseek-r1",
    "qwen":         "qwen-2.5",
    "qwen3":        "qwen-3",
    "mistral":      "mistral-nemo",
    "phi":          "phi-4",
}

IMAGE = {
    "flux":         "flux",
    "fluxpro":      "flux-pro",
    "fluxrealism":  "flux-realism",
    "sdxl":         "sdxl-turbo",
    "playground":   "playground-v2.5",
    "dalle3":       "dall-e-3",
}

VIDEO = {
    "sora":  "sora",
    "veo3":  "veo-3",
}

ROUTES = {}
ROUTES.update({c: ("chat", m)  for c, m in TEXT.items()})
ROUTES.update({c: ("image", m) for c, m in IMAGE.items()})
ROUTES.update({c: ("video", m) for c, m in VIDEO.items()})

RESERVED = {"start", "help", "model"}


# ==========================================================
# КОМАНДЫ
# ==========================================================
@dp.message(Command("start"))
async def on_start(message: types.Message):
    lines = ["BurmaldaAI готов.\n", "ТЕКСТ:"]
    cmds = list(TEXT.keys())
    for i in range(0, len(cmds), 5):
        lines.append("  " + "   ".join("/" + c for c in cmds[i:i + 5]))

    lines.append("\nКАРТИНКИ:")
    cmds = list(IMAGE.keys())
    for i in range(0, len(cmds), 4):
        lines.append("  " + "   ".join("/" + c for c in cmds[i:i + 4]))

    lines.append("\nВИДЕО:")
    lines.append("  " + "   ".join("/" + c for c in VIDEO.keys()))

    lines.append("\nНа фото и видео ставится знак 'BurmaldaAi'.")
    lines.append("Пиши запросы на английском — качество лучше.")
    await message.answer("\n".join(lines))


@dp.message(Command("help"))
async def on_help(message: types.Message):
    await message.answer(
        "BurmaldaAI — бесплатные модели ИИ.\n\n"
        "Примеры:\n"
        "/gpt4o hello\n"
        "/fluxpro beautiful landscape\n"
        "/sora flying car\n\n"
        "Лучшие для картинок: /fluxpro, /fluxrealism."
    )


@dp.message(Command("model"))
async def on_model(message: types.Message):
    lines = ["МОДЕЛИ:\n", "ТЕКСТ:"]
    for c, m in TEXT.items():
        lines.append(f"  /{c}  →  {m}")
    lines.append("\nКАРТИНКИ:")
    for c, m in IMAGE.items():
        lines.append(f"  /{c}  →  {m}")
    lines.append("\nВИДЕО:")
    for c, m in VIDEO.items():
        lines.append(f"  /{c}  →  {m}")
    await message.answer("\n".join(lines))


@dp.message(F.text.startswith("/"))
async def on_command(message: types.Message):
    if not message.text:
        return

    parts = message.text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    prompt = parts[1].strip() if len(parts) > 1 else None

    if cmd in RESERVED:
        return

    if cmd not in ROUTES:
        await message.answer(f"Нет команды /{cmd}. Список: /start")
        return

    if not prompt:
        await message.answer(f"Напиши: /{cmd} твой запрос")
        return

    kind, model = ROUTES[cmd]
    status = await message.answer(f"Генерирую ({model})...")

    try:
        if kind == "chat":
            r = await ai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            text = (r.choices[0].message.content or "").strip() or "(пустой ответ)"
            await status.edit_text(text[:4000])

        elif kind == "image":
            r = await ai.images.generate(
                prompt=prompt, model=model, response_format="url"
            )
            url = r.data[0].url

            async with aiohttp.ClientSession() as s:
                async with s.get(url) as resp:
                    data = await resp.read()

            marked = watermark_image(data)
            await status.delete()
            await message.answer_photo(
                BufferedInputFile(marked.read(), filename="img.jpg"),
                caption=model
            )

        elif kind == "video":
            from g4f.Provider import HuggingFaceMedia
            hf = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)
            r = await hf.media.generate(
                model=model, prompt=prompt, response_format="url"
            )
            url = r.data[0].url

            async with aiohttp.ClientSession() as s:
                async with s.get(url) as resp:
                    data = await resp.read()

            marked = watermark_video(data)
            await status.delete()
            await message.answer_video(
                BufferedInputFile(marked.read(), filename="vid.mp4"),
                caption=model
            )

    except Exception as e:
        log.exception(f"Error {model}: {e}")
        try:
            await status.edit_text(f"Ошибка: {str(e)[:250]}")
        except Exception:
            await message.answer(f"Ошибка: {str(e)[:250]}")


@dp.message()
async def on_other(message: types.Message):
    await message.answer("Используй команды. Список: /start")


# ==========================================================
# ГЛОБАЛЬНЫЙ ПЕРЕХВАТ ОШИБОК
# ==========================================================
@dp.errors()
async def on_error(event: ErrorEvent):
    log.exception(f"Global error: {event.exception}")
    try:
        if event.update.message:
            await event.update.message.answer(f"Ошибка: {str(event.exception)[:200]}")
    except Exception:
        pass


# ==========================================================
# ЗАПУСК
# ==========================================================
async def main():
    log.info("=== START ===")
    log.info(f"Routes: {len(ROUTES)}")
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Webhook deleted, polling...")
    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())


if __name__ == "__main__":
    asyncio.run(main())
