import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from g4f.client import AsyncClient

# === КОНФИГ ===
TELEGRAM_TOKEN = "ТВОЙ_НОВЫЙ_ТОКЕН"
HF_TOKEN = "hf_..."  # Оставь, если используешь HuggingFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
g4f_client = AsyncClient()

# === КОМАНДЫ (ТЕКСТ) ===
TEXT_COMMANDS = {
    # OpenAI
    "gpt4o": "gpt-4o",
    "gpt4omini": "gpt-4o-mini",
    "gpt41": "gpt-4.1",
    "gpt35": "gpt-3.5-turbo",
    # Anthropic
    "claude3": "claude-3-haiku",
    "claude35": "claude-3.5-sonnet",
    # Google
    "gemini": "gemini-1.5-pro",
    "gemini2": "gemini-2.0-flash",
    # Meta
    "llama3": "llama-3.1-70b",
    "llama4": "llama-4",
    # DeepSeek
    "deepseek": "deepseek-v3",
    "deepseekr1": "deepseek-r1",
    # Qwen
    "qwen": "qwen-2.5",
}

# === КОМАНДЫ (КАРТИНКИ) ===
# Добавил модели, которые реально работают через g4f и дают лучшее качество
IMAGE_COMMANDS = {
    "flux": "flux",
    "fluxpro": "flux-pro",
    "fluxrealism": "flux-realism",
    "sdxl": "sdxl-turbo",
    "playground": "playground-v2.5",
    "dalle3": "dall-e-3",  # Работает только если есть cookies, но команда будет
}

# === КОМАНДЫ (ВИДЕО) ===
VIDEO_COMMANDS = {
    "sora": "sora",
}

# Собираем всё в один словарь
ALL_COMMANDS = {}
for cmd, model in TEXT_COMMANDS.items():
    ALL_COMMANDS[cmd] = ("chat", model)
for cmd, model in IMAGE_COMMANDS.items():
    ALL_COMMANDS[cmd] = ("image", model)
for cmd, model in VIDEO_COMMANDS.items():
    ALL_COMMANDS[cmd] = ("video", model)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lines = ["BurmaldaAI готов.\n"]
    lines.append("ТЕКСТ: " + ", ".join("/" + c for c in TEXT_COMMANDS.keys()))
    lines.append("КАРТИНКИ: " + ", ".join("/" + c for c in IMAGE_COMMANDS.keys()))
    lines.append("ВИДЕО: " + ", ".join("/" + c for c in VIDEO_COMMANDS.keys()))
    lines.append("\nПиши запросы на английском для лучшего качества.")
    await message.answer("\n".join(lines))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "BurmaldaAI — доступ к бесплатным ИИ-моделям.\n\n"
        "Примеры:\n"
        "/gpt4o hello\n"
        "/flux a beautiful landscape\n"
        "/sora a flying car\n\n"
        "Важно: для картинок используй /fluxpro или /fluxrealism — они лучше стандартного flux."
    )


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    lines = ["ТЕКСТ:"]
    for cmd, model in TEXT_COMMANDS.items():
        lines.append(f"  /{cmd} → {model}")
    lines.append("\nКАРТИНКИ:")
    for cmd, model in IMAGE_COMMANDS.items():
        lines.append(f"  /{cmd} → {model}")
    lines.append("\nВИДЕО:")
    for cmd, model in VIDEO_COMMANDS.items():
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
            await status.delete()
            await message.answer_photo(resp.data[0].url, caption=model)

        elif kind == "video":
            # Пробуем через HuggingFaceMedia (нужен HF_TOKEN)
            from g4f.Provider import HuggingFaceMedia
            hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)
            result = await hf_client.media.generate(
                model=model,
                prompt=prompt,
                response_format="url"
            )
            await status.delete()
            await message.answer_video(result.data[0].url, caption=model)

    except Exception as e:
        logger.exception(f"Ошибка {model}: {e}")
        await status.edit_text(f"Ошибка: {str(e)[:300]}")


async def main():
    logger.info("=== СТАРТ ===")
    await dp.start_polling(bot, allowed_updates=types.Update.model_fields.keys())


if __name__ == "__main__":
    asyncio.run(main())
