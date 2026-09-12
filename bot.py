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

# Хранилище активных команд: { "gpt35turbo": ("chat", "gpt-3.5-turbo"), ... }
COMMAND_MAP = {}


async def build_commands():
    """Собирает команды из доступных моделей G4F. Не падает при ошибке."""
    global COMMAND_MAP
    COMMAND_MAP = {}

    # Текстовые модели
    try:
        models = g4f_client.models.get_all()
        for m in models:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            COMMAND_MAP[cmd] = ("chat", m)
        logger.info(f"Загружено текстовых моделей: {len(models)}")
    except Exception as e:
        logger.exception(f"Ошибка загрузки текстовых моделей: {e}")
        # Фоллбэк
        COMMAND_MAP["gpt35turbo"] = ("chat", "gpt-3.5-turbo")
        COMMAND_MAP["gpt4"] = ("chat", "gpt-4")

    # Модели для картинок
    try:
        img_models = g4f_client.models.get_image()
        for m in img_models:
            cmd = m.replace("-", "").replace(".", "").replace("_", "").lower()
            COMMAND_MAP[cmd] = ("image", m)
        logger.info(f"Загружено моделей для картинок: {len(img_models)}")
    except Exception as e:
        logger.exception(f"Ошибка загрузки моделей для картинок: {e}")
        COMMAND_MAP["gptimg2"] = ("image", "dall-e-3")
        COMMAND_MAP["flux"] = ("image", "flux")

    # Видео модели (только доступные через HF)
    COMMAND_MAP["sora"] = ("video", "sora-2")
    COMMAND_MAP["veo"] = ("video", "veo-3.1-fast")

    logger.info(f"Итого команд: {len(COMMAND_MAP)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветствие со списком команд."""
    lines = ["Привет! Доступные команды:\n"]

    text_cmds = [c for c, (t, _) in COMMAND_MAP.items() if t == "chat"]
    img_cmds = [c for c, (t, _) in COMMAND_MAP.items() if t == "image"]
    vid_cmds = [c for c, (t, _) in COMMAND_MAP.items() if t == "video"]

    if text_cmds:
        lines.append(f"Текст: {', '.join('/' + c for c in text_cmds[:20])}")
    if img_cmds:
        lines.append(f"Картинки: {', '.join('/' + c for c in img_cmds)}")
    if vid_cmds:
        lines.append(f"Видео: {', '.join('/' + c for c in vid_cmds)}")

    await update.message.reply_text("\n".join(lines))


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Универсальный обработчик для всех динамических команд."""
    # context.args — это список аргументов после команды
    # Например, для "/gpt4 привет мир" это будет ["привет", "мир"]
    prompt = " ".join(context.args) if context.args else None

    # Извлекаем имя команды из текста сообщения (без слэша)
    # context.args не содержит саму команду, поэтому парсим текст
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

    # Загружаем команды (не падаем при ошибке)
    await build_commands()

    # Создаём Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрируем /start
    application.add_handler(CommandHandler("start", start))

    # Регистрируем универсальный обработчик для всех остальных команд
    # Используем filters.COMMAND, чтобы он ловил только команды
    from telegram.ext import filters
    application.add_handler(CommandHandler(
        list(COMMAND_MAP.keys()),  # список имён команд без слэша
        handle_command
    ))

    logger.info("Запускаю polling...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("=== БОТ ОСТАНОВЛЕН ===")


if __name__ == "__main__":
    asyncio.run(main())
