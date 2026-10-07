import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from .config import BOT_TOKEN, DB_PATH
from .database import Database
from .handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("happ_bot")


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "❌ ОШИБКА: BOT_TOKEN не задан!\n"
            "Пожалуйста, укажите токен вашего Telegram-бота в файле .env:\n"
            "BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz\n"
        )
        sys.exit(1)

    db = Database(DB_PATH)
    await db.init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    bot.db = db

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logger.info("🚀 Бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот завершил работу.")

