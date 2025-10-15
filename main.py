import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from bot.core.config import BOT_TOKEN
from bot.handlers import register_all_handlers

from bot.utils.processing import check_ffmpeg_installed

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)



if not os.path.exists("./downloads"):
    os.makedirs("./downloads")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)
dp = Dispatcher()


async def main():

    if not await check_ffmpeg_installed():
        error_msg = (
            "\n"
            "===========================================================\n"
            "!!! КРИТИЧЕСКАЯ ОШИБКА: FFmpeg не найден !!!\n"
            "Бот не может работать без FFmpeg. Пожалуйста, установите его \n"
            "и убедитесь, что 'ffmpeg.exe' и 'ffprobe.exe' прописаны в PATH.\n"
            "===========================================================\n"
        )
        print(error_msg, file=sys.stderr)
        sys.exit(1)


    register_all_handlers(dp, bot)
    logging.info("Все хэндлеры успешно зарегистрированы. Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by KeyboardInterrupt.")