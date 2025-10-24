import asyncio
import logging
import os
import sys
import subprocess
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


async def check_for_updates():
    """Checks for and applies updates from the Git repository."""
    try:
        # 1. Проверяем, являемся ли мы в Git-репозитории
        subprocess.run(['git', 'status'], check=True, capture_output=True)
        
        print("Проверка обновлений из репозитория...")
        
        # 2. Получаем последние изменения
        result = subprocess.run(
            ['git', 'pull', 'origin', 'master'], 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        if "Already up to date." not in result.stdout and "Already up-to-date." not in result.stdout:
            print("Обнаружены и применены обновления кода. Установка зависимостей...")
            
            # 3. Обновляем зависимости с помощью Poetry
            subprocess.run(['poetry', 'install'], check=True)

            print("Обновления применены. Перезапуск для применения изменений...")
            # 4. Перезапускаем скрипт (критически важно для применения изменений)
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Код уже актуален. Запуск бота...")

    except subprocess.CalledProcessError as e:
        # Если git status не сработал или git pull не сработал
        print("Не удалось выполнить git-команды. Возможно, это не Git-репозиторий или нет прав доступа.")
        # Продолжаем выполнение, если не удалось обновиться
    except FileNotFoundError:
        print("Команда 'git' или 'poetry' не найдена. Проверьте ваш PATH.")
        # Продолжаем выполнение, если не удалось обновить зависимости
    except Exception as e:
        print(f"Ошибка при самообновлении: {e}")

async def main():
    await check_for_updates()

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