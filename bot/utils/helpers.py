import asyncio
import logging
import os
import shutil

import yt_dlp


from bot.core.config import MIN_FILE_SIZE_BYTES, RETRY_DOWNLOAD_ATTEMPTS, RETRY_SEND_ATTEMPTS

async def cleanup_files(*filenames, delay=0):
    """Безопасно удаляет указанные временные файлы с опциональной задержкой."""
    if delay > 0:
        await asyncio.sleep(delay)
    for filename in filenames:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                logging.info(f"Временный файл {filename} удален.")
            except OSError as e:
                logging.error(f"Не удалось удалить временный файл {filename}: {e}")


async def validate_video_file(video_path: str, min_duration=1.0) -> bool:
    """Валидирует файл: размер > MIN_FILE_SIZE_BYTES и длительность > min_duration."""

    from bot.utils.processing import get_video_duration

    if not os.path.exists(video_path): return False
    size = os.path.getsize(video_path)
    if size < MIN_FILE_SIZE_BYTES:
        logging.warning(f"Файл {video_path} слишком мал: {size} байт")
        return False
    duration = await get_video_duration(video_path)
    if duration < min_duration:
        logging.warning(f"Длительность {video_path} слишком мала: {duration} сек")
        return False
    logging.info(f"Файл {video_path} валиден: {size // 1024} КБ, {duration:.1f} сек")
    return True


async def validate_audio_file(audio_path: str, min_duration=1.0) -> bool:
    """Валидирует аудио файл: размер > MIN_FILE_SIZE_BYTES и длительность > min_duration."""

    from bot.utils.processing import get_audio_duration

    if not os.path.exists(audio_path): return False
    size = os.path.getsize(audio_path)
    if size < MIN_FILE_SIZE_BYTES:
        logging.warning(f"Аудио файл {audio_path} слишком мал: {size} байт")
        return False
    duration = await get_audio_duration(audio_path)
    if duration < min_duration:
        logging.warning(f"Длительность {audio_path} слишком мала: {duration} сек")
        return False
    logging.info(f"Аудио файл {audio_path} валиден: {size // 1024} КБ, {duration:.1f} сек")
    return True


async def download_with_retry(ydl_class, ydl_opts, link, max_attempts=RETRY_DOWNLOAD_ATTEMPTS):
    """Скачивает с retry и валидацией."""
    for attempt in range(1, max_attempts + 1):
        # Инициализируем путь к файлу для корректной очистки, если произойдет сбой
        downloaded_file = None
        try:
            with ydl_class.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)

                downloaded_file = ydl.prepare_filename(info)

                if not isinstance(downloaded_file, str):
                    raise TypeError(f"ydl.prepare_filename вернул некорректный тип ({type(downloaded_file)}).")

                # 3. Валидация
                if not os.path.exists(downloaded_file):
                    raise Exception(f"Файл {downloaded_file} не найден после скачивания.")

                if await validate_video_file(downloaded_file):
                    return downloaded_file
                else:
                    logging.warning(f"Попытка {attempt}: файл не валиден, удаляю")
                    await cleanup_files(downloaded_file)  # Удаление невалидного файла

        except Exception as e:
            # Логгирование ошибки и переход к следующей попытке
            logging.warning(f"Попытка {attempt} скачивания провалилась: {e}")

            # Очистка, если файл был найден, но что-то пошло не так
            if downloaded_file and os.path.exists(downloaded_file):
                await cleanup_files(downloaded_file)

        if attempt < max_attempts:
            await asyncio.sleep(5 * attempt)

    return None


async def send_with_retry(send_func, *args, max_attempts=RETRY_SEND_ATTEMPTS, **kwargs):
    """Отправляет с retry."""
    for attempt in range(1, max_attempts + 1):
        try:
            return await send_func(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Попытка {attempt} отправки провалилась: {e}")
            if attempt < max_attempts:
                await asyncio.sleep(3 * attempt)
    raise Exception("Не удалось отправить после всех попыток")