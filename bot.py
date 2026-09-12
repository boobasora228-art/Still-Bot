import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
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

# Асинхронные клиенты G4F
g4f_client = AsyncClient()
hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)

# Хранилище: {"gpt4": ("chat", "gpt-4"), "flux": ("image", "flux"), ...}
COMMAND_MAP = {}

# Список всех текстовых моделей из g4f (для команды /model)
TEXT_MODELS = []
IMAGE_MODELS = []
VIDEO_MODELS = []


async def build_commands():
    """Собирает команды из доступных моделей G4F. Не падает при ошибке."""
    global COMMAND_MAP, TEXT_MODELS, IMAGE_MODELS, VIDEO_MODELS
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
    VIDEO_MODELS = ["sora", "veo"]
    COMMAND_MAP["sora"] = ("video", "sora")
    COMMAND_MAP["veo"] = ("video", "veo")

    logger.info(f"Итого команд: {len(COMMAND_MAP)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    await update.message.reply_text("\n".join(lines))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(text)


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает доступные модели для выбора."""
    # Если аргументы не переданы — показываем список
    if not context.args:
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
        await update.message.reply_text("\n".join(lines))
        return

    # Если пользователь указал модель — подтверждаем
    model_name = context.args[0].lower()
    if model_name in COMMAND_MAP:
        kind, real_model = COMMAND_MAP[model_name]
        await update.message.reply_text(
            f"Модель: {real_model}\nТип: {kind}\n"
            f"Используй: /{model_name} твой запрос"
        )
    else:
        await update.message.reply_text(f"Модель {model_name} не найдена. Используй /model для списка.")


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Универсальный обработчик для всех динамических команд."""
    prompt = " ".join(context.args) if context.args else None

    if not update.message or not update.message.text:
        return

    parts = update.message.text[1:].split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd not in COMMAND_MAP:
        await update.message.reply_text(f"Неизвестная команда: /{cmd}. Напиши /start для списка.")
        return

    if not prompt:
        await update.message.reply_text(f"Использование: /{cmd} ваш запрос")
        return

    kind, model = COMMAND_MAP[cmd]
    status_msg = await update.message.reply_text(f"Генерирую через {model}...")

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
            await update.message.reply_photo(url, caption=model)

        elif kind == "video":
            result = await hf_client.media.generate(
                model=model,
                prompt=prompt,
                response_format="url"
            )
            video_url = result.data[0].url
            await status_msg.delete()
            await update.message.reply_video(video_url, caption=model)

    except Exception as e:
        logger.exception(f"Ошибка генерации для {model}: {e}")
        await status_msg.edit_text(f"Ошибка: {str(e)[:500]}")


async def main() -> None:
    """Точка входа."""
    logger.info("=== СТАРТ БОТА ===")

    await build_commands()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Стандартные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("model", model_command))

    # Универсальный обработчик для всех динамических команд
    all_cmds = list(COMMAND_MAP.keys()) + ["start", "help", "model"]
    application.add_handler(CommandHandler(all_cmds, handle_command))

    logger.info("Запускаю polling...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("=== БОТ ОСТАНОВЛЕН ===")


if __name__ == "__main__":
    asyncio.run(main())
