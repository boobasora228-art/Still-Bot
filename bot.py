import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from g4f.client import AsyncClient
from g4f.Provider import HuggingFaceMedia

# === КОНФИГ ===
TELEGRAM_TOKEN = "8931135477:AAGkh2HUo2bE2OKiGO0t8fIN3iajV2tIeMY"  # ЗАМЕНИ НА НОВЫЙ
HF_TOKEN = "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"  # ЗАМЕНИ НА НОВЫЙ

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Асинхронные клиенты G4F
g4f_client = AsyncClient()
hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)

# Хранилище: {"gpt4": ("chat", "gpt-4"), "flux": ("image", "flux"), ...}
COMMAND_MAP = {}

# Списки моделей
TEXT_MODELS = []
IMAGE_MODELS = []
VIDEO_MODELS = ["sora", "veo"]


async def build_commands():
    """Собирает команды из доступных моделей G4F. Не падает при ошибке."""
    global COMMAND_MAP, TEXT_MODELS, IMAGE_MODELS
    COMMAND_MAP = {}

    # === Текстовые модели ===
    try:
        TEXT_MODELS = g4f_client.models.get_all()
        logger.info(f"Загружено текстовых моделей: {len(TEXT_MODELS)}")
    except Exception as e:
        logger.exception(f"Ошибка загрузки текстовых моделей: {e}")
        TEXT_MODELS = ["gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"]

    for m in TEXT_MODELS:
        cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
        COMMAND_MAP[cmd] = ("chat", m)

    # === Модели для картинок ===
    try:
        IMAGE_MODELS = g4f_client.models.get_image()
        logger.info(f"Загружено моделей для картинок: {len(IMAGE_MODELS)}")
    except Exception as e:
        logger.exception(f"Ошибка загрузки моделей для картинок: {e}")
        IMAGE_MODELS = ["dall-e-3", "flux", "sdxl"]

    for m in IMAGE_MODELS:
        cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
        COMMAND_MAP[cmd] = ("image", m)

    # === Видео модели ===
    for m in VIDEO_MODELS:
        COMMAND_MAP[m] = ("video", m)

    logger.info(f"Итого команд: {len(COMMAND_MAP)}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветствие со списком команд."""
    lines = ["Привет! Я BurmaldaAI.\n"]

    text_cmds = [c for c, (t, _) in COMMAND_MAP.items() if t == "chat"]
    img_cmds = [c for c, (t, _) in COMMAND_MAP.items() if t == "image"]
    vid_cmds = [c for c, (t, _) in COMMAND_MAP.items() if t == "video"]

    if text_cmds:
        lines.append(f"Текст: {', '.join('/' + c for c in text_cmds[:15])}")
    if img_cmds:
        lines.append(f"Картинки: {', '.join('/' + c for c in img_cmds)}")
    if vid_cmds:
        lines.append(f"Видео: {', '.join('/' + c for c in vid_cmds)}")

    lines.append("\nИспользуй /model чтобы выбрать модель.")
    lines.append("Лучше писать на английском для лучших результатов.")

    await message.answer("\n".join(lines))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Информация о боте и рекомендация писать на английском."""
    text = (
        "BurmaldaAI — бот с доступом к бесплатным ИИ-моделям.\n\n"
        "Доступные типы моделей:\n"
        "• Текст — GPT-4, GPT-3.5, Llama, Claude и другие\n"
        "• Картинки — DALL-E, Flux, SDXL и другие\n"
        "• Видео — Sora, Veo\n\n"
        "Как использовать:\n"
        "• /gpt4 привет — генерация текста\n"
        "• /flux кот — генерация картинки\n"
        "• /sora город — генерация видео\n"
        "• /model — выбрать модель из списка\n\n"
        "Важно: большинство моделей лучше работают с запросами "
        "на английском языке. Пиши на русском только если модель это поддерживает."
    )
    await message.answer(text)


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    """Показывает доступные модели для выбора."""
    # Если аргументы не переданы — показываем список
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        lines = ["Доступные модели:\n"]

        lines.append("Текст:")
        for m in TEXT_MODELS[:20]:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            lines.append(f"  /{cmd}")

        lines.append("\nКартинки:")
        for m in IMAGE_MODELS[:10]:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            lines.append(f"  /{cmd}")

        lines.append("\nВидео:")
        for m in VIDEO_MODELS:
            lines.append(f"  /{m}")

        lines.append("\nПример: /model gpt4")
        await message.answer("\n".join(lines))
        return

    # Если пользователь указал модель — подтверждаем
    model_name = args[1].lower()
    if model_name in COMMAND_MAP:
        kind, real_model = COMMAND_MAP[model_name]
        await message.answer(
            f"Модель: {real_model}\nТип: {kind}\n"
            f"Используй: /{model_name} твой запрос"
        )
    else:
        await message.answer(f"Модель {model_name} не найдена. Используй /model для списка.")


@dp.message(F.text.startswith("/"))
async def handle_command(message: types.Message):
    """Универсальный обработчик для всех динамических команд."""
    parts = message.text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    prompt = parts[1] if len(parts) > 1 else None

    # Пропускаем стандартные команды
    if cmd in ("start", "help", "model"):
        return

    if cmd not in COMMAND_MAP:
        await message.answer(f"Неизвестная команда: /{cmd}. Напиши /start для списка.")
        return

    if not prompt:
        await message.answer(f"Использование: /{cmd} ваш запрос")
        return

    kind, model = COMMAND_MAP[cmd]
    status_msg = await message.answer(f"Генерирую через {model}...")

    try:
        if kind == "chat":
            response = await g4f_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content
            await status_msg.edit_text(text[:4000])

        elif kind == "image":
            response = await g4f_client.images.generate(
                prompt=prompt,
                model=model,
                response_format="url"
            )
            url = response.data[0].url
            await status_msg.delete()
            await message.answer_photo(url, caption=model)

        elif kind == "video":
            result = await hf_client.media.generate(
                model=model,
                prompt=prompt,
                response_format="url"
            )
            video_url = result.data[0].url
            await status_msg.delete()
            await message.answer_video(video_url, caption=model)

    except Exception as e:
        logger.exception(f"Ошибка генерации для {model}: {e}")
        await status_msg.edit_text(f"Ошибка: {str(e)[:500]}")


async def main():
    """Точка входа."""
    logger.info("=== СТАРТ БОТА ===")

    await build_commands()

    logger.info("Запускаю polling...")
    # ВАЖНО: allowed_updates=Update.ALL_TYPES — чтобы ловить все типы обновлений
    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())
    logger.info("=== БОТ ОСТАНОВЛЕН ===")


if __name__ == "__main__":
    asyncio.run(main())
