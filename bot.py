import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from g4f.client import AsyncClient
from g4f.Provider import HuggingFaceMedia

# === КОНФИГ ===
TELEGRAM_TOKEN = "8931135477:AAGkh2HUo2bE2OKiGO0t8fIN3iajV2tIeMY"  # ЗАМЕНИ НА НОВЫЙ
HF_TOKEN = "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"  # ЗАМЕНИ НА НОВЫЙ

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
g4f_client = AsyncClient()
hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)

# Здесь будет храниться всё, что найдём
ALL_COMMANDS = {}      # {"gpt4": ("chat", "gpt-4"), "flux": ("image", "flux"), ...}
TEXT_MODELS = []       # список текстовых моделей
IMAGE_MODELS = []      # список моделей для картинок
VIDEO_MODELS = []      # список видео-моделей


async def collect_all_models():
    """Собирает модели из всех доступных источников g4f."""
    global ALL_COMMANDS, TEXT_MODELS, IMAGE_MODELS, VIDEO_MODELS
    ALL_COMMANDS = {}

    # === 1. Текстовые модели ===
    try:
        TEXT_MODELS = g4f_client.models.get_all()
        logger.info(f"Текстовых моделей: {len(TEXT_MODELS)}")
    except Exception as e:
        logger.warning(f"Не удалось получить текстовые модели: {e}")
        TEXT_MODELS = []

    # === 2. Модели для картинок ===
    try:
        IMAGE_MODELS = g4f_client.models.get_image()
        logger.info(f"Моделей для картинок: {len(IMAGE_MODELS)}")
    except Exception as e:
        logger.warning(f"Не удалось получить модели картинок: {e}")
        IMAGE_MODELS = []

    # === 3. Видео-модели (два способа) ===
    # Способ 1: через HuggingFaceMedia
    try:
        video_hf = hf_client.models.get_video()
        VIDEO_MODELS.extend(video_hf)
        logger.info(f"Видео через HF: {video_hf}")
    except Exception as e:
        logger.warning(f"HF видео недоступны: {e}")

    # Способ 2: через провайдер Video (без API-ключа)
    try:
        from g4f.Provider import Video
        video_client = AsyncClient(provider=Video)
        video_plain = video_client.models.get_video()
        for v in video_plain:
            if v not in VIDEO_MODELS:
                VIDEO_MODELS.append(v)
        logger.info(f"Видео через Video-провайдер: {video_plain}")
    except Exception as e:
        logger.warning(f"Video-провайдер недоступен: {e}")

    # === 4. Формируем команды ===
    for m in TEXT_MODELS:
        cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
        if cmd:
            ALL_COMMANDS[cmd] = ("chat", m)

    for m in IMAGE_MODELS:
        cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
        if cmd and cmd not in ALL_COMMANDS:
            ALL_COMMANDS[cmd] = ("image", m)

    for m in VIDEO_MODELS:
        cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
        if cmd and cmd not in ALL_COMMANDS:
            ALL_COMMANDS[cmd] = ("video", m)

    logger.info(f"Всего команд: {len(ALL_COMMANDS)}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lines = ["BurmaldaAI готов.\n"]
    lines.append(f"Текстовых моделей: {len(TEXT_MODELS)}")
    lines.append(f"Моделей для картинок: {len(IMAGE_MODELS)}")
    lines.append(f"Видео-моделей: {len(VIDEO_MODELS)}")
    lines.append("")
    lines.append("Все команды: /model")
    lines.append("Информация: /help")
    await message.answer("\n".join(lines))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "BurmaldaAI — доступ ко всем доступным моделям G4F.\n\n"
        "Команды создаются автоматически из списка моделей.\n"
        "Используй /model чтобы увидеть полный список.\n\n"
        "Пиши запросы на английском — модели понимают его лучше."
    )


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    lines = []

    if TEXT_MODELS:
        lines.append("ТЕКСТ:")
        for m in TEXT_MODELS[:30]:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            lines.append(f"  /{cmd}")

    if IMAGE_MODELS:
        lines.append("\nКАРТИНКИ:")
        for m in IMAGE_MODELS[:20]:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            lines.append(f"  /{cmd}")

    if VIDEO_MODELS:
        lines.append("\nВИДЕО:")
        for m in VIDEO_MODELS:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            lines.append(f"  /{cmd}")

    if not lines:
        await message.answer("Модели не загружены. Попробуй позже.")
        return

    # Telegram ограничивает длину сообщения
    text = "\n".join(lines)
    if len(text) > 4000:
        # Разбиваем на части
        for i in range(0, len(text), 4000):
            await message.answer(text[i:i+4000])
    else:
        await message.answer(text)


@dp.message(F.text.startswith("/"))
async def handle_command(message: types.Message):
    parts = message.text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    prompt = parts[1] if len(parts) > 1 else None

    if cmd in ("start", "help", "model"):
        return

    if cmd not in ALL_COMMANDS:
        await message.answer(f"Нет команды /{cmd}. Смотри /model")
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
            await status.delete()
            await message.answer_photo(resp.data[0].url, caption=model)

        elif kind == "video":
            # Пробуем через HF
            try:
                result = await hf_client.media.generate(
                    model=model,
                    prompt=prompt,
                    response_format="url"
                )
                video_url = result.data[0].url
            except Exception:
                # Если не вышло — пробуем через Video-провайдер
                from g4f.Provider import Video
                vc = AsyncClient(provider=Video)
                result = await vc.media.generate(
                    model=model,
                    prompt=prompt,
                    response_format="url"
                )
                video_url = result.data[0].url

            await status.delete()
            await message.answer_video(video_url, caption=model)

    except Exception as e:
        logger.exception(f"Ошибка {model}: {e}")
        await status.edit_text(f"Ошибка: {str(e)[:300]}")


async def main():
    logger.info("=== СТАРТ ===")
    await collect_all_models()
    logger.info(f"Команд: {len(ALL_COMMANDS)}")
    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())


if __name__ == "__main__":
    asyncio.run(main())
