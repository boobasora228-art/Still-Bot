import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from g4f.client import AsyncClient

# === КОНФИГ ===
TELEGRAM_TOKEN = "8931135477:AAGkh2HUo2bE2OKiGO0t8fIN3iajV2tIeMY"  # ЗАМЕНИ НА НОВЫЙ
HF_TOKEN = os.getenv("HF_TOKEN", "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")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
g4f_client = AsyncClient()

# Жёстко задаём команды, которые точно должны работать
COMMAND_MAP = {
    "gpt4": ("chat", "gpt-4o"),
    "gpt35turbo": ("chat", "gpt-3.5-turbo"),
    "gpt4o": ("chat", "gpt-4o"),
    "gpt4omini": ("chat", "gpt-4o-mini"),
    "llama3": ("chat", "llama-3.1-70b"),
    "flux": ("image", "flux"),
    "sdxl": ("image", "sdxl"),
    "sora": ("video", "sora"),
}

# Список моделей для /model
TEXT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "llama-3.1-70b"]
IMAGE_MODELS = ["flux", "sdxl"]
VIDEO_MODELS = ["sora"]

async def build_commands():
    """Пытаемся подтянуть модели, но не падаем при ошибке."""
    global COMMAND_MAP
    try:
        models = g4f_client.models.get_all()
        logger.info(f"G4F вернул {len(models)} моделей")
        for m in models:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            if cmd not in COMMAND_MAP:
                COMMAND_MAP[cmd] = ("chat", m)
    except Exception as e:
        logger.warning(f"Не удалось загрузить модели G4F: {e}")
        logger.warning("Использую только жёстко заданные команды")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lines = ["BurmaldaAI готов.\n", "Текст: /gpt4, /gpt35turbo, /gpt4o, /gpt4omini, /llama3"]
    lines.append("Картинки: /flux, /sdxl")
    lines.append("Видео: /sora")
    lines.append("\n/model — список моделей")
    lines.append("/help — информация")
    await message.answer("\n".join(lines))

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "BurmaldaAI — доступ к бесплатным ИИ-моделям.\n\n"
        "Примеры:\n"
        "/gpt4 привет\n"
        "/flux кот\n"
        "/sora город\n\n"
        "Пиши запросы на английском — модели понимают его лучше."
    )

@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        lines = ["Текст: " + ", ".join("/" + m.replace("-","").replace(".","").lower() for m in TEXT_MODELS)]
        lines.append("Картинки: " + ", ".join("/" + m for m in IMAGE_MODELS))
        lines.append("Видео: " + ", ".join("/" + m for m in VIDEO_MODELS))
        await message.answer("\n".join(lines))
        return
    name = args[1].lower()
    if name in COMMAND_MAP:
        kind, model = COMMAND_MAP[name]
        await message.answer(f"Модель: {model}\nТип: {kind}\nИспользуй: /{name} запрос")
    else:
        await message.answer("Не найдено. Смотри /model")

@dp.message(F.text.startswith("/"))
async def handle_command(message: types.Message):
    parts = message.text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    prompt = parts[1] if len(parts) > 1 else None

    if cmd in ("start", "help", "model"):
        return

    if cmd not in COMMAND_MAP:
        await message.answer(f"Нет команды /{cmd}. Смотри /start")
        return

    if not prompt:
        await message.answer(f"Напиши: /{cmd} твой запрос")
        return

    kind, model = COMMAND_MAP[cmd]
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
            await status.delete()
            await message.answer_photo(resp.data[0].url, caption=model)

        elif kind == "video":
            await status.edit_text("Видео пока недоступно через этот провайдер.")

    except Exception as e:
        logger.exception(f"Ошибка {model}: {e}")
        await status.edit_text(f"Ошибка: {str(e)[:300]}")

async def main():
    logger.info("=== СТАРТ ===")
    await build_commands()
    logger.info(f"Команд: {len(COMMAND_MAP)}")
    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())

if __name__ == "__main__":
    asyncio.run(main())
