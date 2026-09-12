import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
token = os.getenv("BOT_TOKEN")
print(f"STARTING. Token: {token[:10] if token else 'NONE'}...")

bot = Bot(token=token)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("OK")

if __name__ == "__main__":
    import asyncio
    print("POLLING...")
    asyncio.run(dp.start_polling(bot))
