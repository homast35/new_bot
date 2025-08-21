import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove
from recipes_handler import register_handlers
from token_data import BOT_TOKEN

async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    # Регистрация всех обработчиков
    register_handlers(dp)

    # Старт бота
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())