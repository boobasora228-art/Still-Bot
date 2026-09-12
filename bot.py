# === ЯВНО ДОБАВЛЯЕМ КОМАНДЫ ===
MANUAL_COMMANDS = {
    # Текст — OpenAI
    "gpt4o": ("chat", "gpt-4o"),
    "gpt4omini": ("chat", "gpt-4o-mini"),
    "gpt41": ("chat", "gpt-4.1"),
    "gpt35turbo": ("chat", "gpt-3.5-turbo"),

    # Текст — Anthropic (Claude)
    "claude3haiku": ("chat", "claude-3-haiku"),
    "claude3sonnet": ("chat", "claude-3-sonnet"),
    "claude3opus": ("chat", "claude-3-opus"),
    "claude35sonnet": ("chat", "claude-3.5-sonnet"),

    # Текст — Google (Gemini)
    "gemini15pro": ("chat", "gemini-1.5-pro"),
    "gemini20flash": ("chat", "gemini-2.0-flash"),
    "gemini25pro": ("chat", "gemini-2.5-pro"),

    # Текст — Meta (Llama)
    "llama3": ("chat", "llama-3"),
    "llama31": ("chat", "llama-3.1"),
    "llama32": ("chat", "llama-3.2"),
    "llama33": ("chat", "llama-3.3"),
    "llama4": ("chat", "llama-4"),

    # Текст — Mistral
    "mistral": ("chat", "mistral-nemo"),
    "mistralsmall": ("chat", "mistral-small"),

    # Текст — Qwen
    "qwen2": ("chat", "qwen-2"),
    "qwen25": ("chat", "qwen-2.5"),
    "qwen3": ("chat", "qwen-3"),

    # Текст — DeepSeek
    "deepseekv3": ("chat", "deepseek-v3"),
    "deepseekr1": ("chat", "deepseek-r1"),

    # Текст — Microsoft
    "phi35": ("chat", "phi-3.5"),
    "phi4": ("chat", "phi-4"),

    # Картинки
    "dalle3": ("image", "dall-e-3"),
    "gptimage": ("image", "gpt-image"),
    "flux": ("image", "flux"),
    "fluxpro": ("image", "flux-pro"),
    "fluxrealism": ("image", "flux-realism"),
    "fluxanime": ("image", "flux-anime"),
    "flux3d": ("image", "flux-3d"),
    "fluxdisney": ("image", "flux-disney"),
    "fluxpixel": ("image", "flux-pixel"),
    "sdxl": ("image", "sdxl-turbo"),
    "playgroundv25": ("image", "playground-v2.5"),

    # Видео
    "sora": ("video", "sora"),
    "veo3": ("video", "veo-3"),
}


async def collect_all_models():
    """Собирает модели из всех доступных источников g4f."""
    global ALL_COMMANDS, TEXT_MODELS, IMAGE_MODELS, VIDEO_MODELS
    ALL_COMMANDS = {}

    # === 1. Автоматически из g4f ===
    try:
        TEXT_MODELS = g4f_client.models.get_all()
        logger.info(f"Текстовых моделей из g4f: {len(TEXT_MODELS)}")
    except Exception as e:
        logger.warning(f"Не удалось получить текстовые модели: {e}")
        TEXT_MODELS = []

    try:
        IMAGE_MODELS = g4f_client.models.get_image()
        logger.info(f"Моделей для картинок из g4f: {len(IMAGE_MODELS)}")
    except Exception as e:
        logger.warning(f"Не удалось получить модели картинок: {e}")
        IMAGE_MODELS = []

    try:
        from g4f.Provider import HuggingFaceMedia
        hf_client = AsyncClient(provider=HuggingFaceMedia, api_key=HF_TOKEN)
        VIDEO_MODELS = hf_client.models.get_video()
        logger.info(f"Видео-моделей из HF: {len(VIDEO_MODELS)}")
    except Exception as e:
        logger.warning(f"Не удалось получить видео-модели: {e}")
        VIDEO_MODELS = []

    # === 2. Формируем команды из автоматически собранных ===
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

    # === 3. Добавляем ручные команды (если их ещё нет) ===
    for cmd, (kind, model) in MANUAL_COMMANDS.items():
        if cmd not in ALL_COMMANDS:
            ALL_COMMANDS[cmd] = (kind, model)
            if kind == "chat" and model not in TEXT_MODELS:
                TEXT_MODELS.append(model)
            elif kind == "image" and model not in IMAGE_MODELS:
                IMAGE_MODELS.append(model)
            elif kind == "video" and model not in VIDEO_MODELS:
                VIDEO_MODELS.append(model)

    logger.info(f"Всего команд: {len(ALL_COMMANDS)}")
