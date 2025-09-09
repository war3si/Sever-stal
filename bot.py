import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TOKEN
from db import init_db
from handlers import router

async def main():
    print("Инициализация...")
    init_db()
    print("Инициализация БД завершена")
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("Bot создан")
    dp = Dispatcher()
    dp.include_router(router)
    print("Перед стартом polling")
    await dp.start_polling(bot)
    print("Polling завершился")

if __name__ == '__main__':
    print("Старт main()")
    asyncio.run(main())
    print("Выход из программы")
