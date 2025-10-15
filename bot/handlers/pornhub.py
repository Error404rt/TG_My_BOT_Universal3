import asyncio
import logging
import tempfile
import shutil
from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
import yt_dlp
import youtube_dl
import os

from bot.core.states import PHStates
from bot.core.config import SLEEP_BETWEEN_CHUNKS
from bot.utils.helpers import cleanup_files, download_with_retry, send_with_retry
from bot.utils.processing import get_video_duration, split_video_chunks, compress_video_if_needed


async def cmd_ph_download(message: types.Message, state: FSMContext):
    await message.answer("Отправьте ссылку на Pornhub видео. Я скачаю и отправлю готовые MP4-чанки. 🔥")
    await state.set_state(PHStates.waiting_for_link)


async def process_ph_link(message: types.Message, state: FSMContext):
    bot = message.bot
    await message.answer("Получил ссылку, скачиваю полностью... 📥")
    link = message.text
    chat_id = message.chat.id
    temp_dir = tempfile.mkdtemp()
    # Примечание: outtmpl должен включать temp_dir
    video_path_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
    video_path = None  # Будет установлено после скачивания

    success = False
    method_used = ""

    try:
        # Метод 1: yt-dlp с retry
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]',
            'outtmpl': video_path_template,
            'noplaylist': True,
        }
        downloaded_path = await download_with_retry(yt_dlp, ydl_opts, link)
        if downloaded_path:
            video_path = downloaded_path
            success = True
            method_used = "yt-dlp"
        else:
            # Метод 2: youtube-dl с retry (fallback)
            ydl_opts['outtmpl'] = video_path_template  # Важно, чтобы template был правильный
            downloaded_path = await download_with_retry(youtube_dl, ydl_opts, link)
            if downloaded_path:
                video_path = downloaded_path
                success = True
                method_used = "youtube-dl"

        if not success or not video_path:
            await bot.send_message(chat_id,
                                   "Не удалось скачать ни одним методом после попыток. Попробуй другую ссылку. ❌")
            return

        await bot.send_message(chat_id, f"Скачано с {method_used}! Обрабатываю... ✅")

        duration = await get_video_duration(video_path)
        file_size = os.path.getsize(video_path)
        await bot.send_message(chat_id, f"Видео: {duration:.1f} сек, {file_size // 1024 // 1024} МБ.")

        with tempfile.TemporaryDirectory() as chunk_dir:
            chunks = await split_video_chunks(video_path, chunk_dir)
            if not chunks:
                await bot.send_message(chat_id, "Ошибка при разрезке. 😔")
                return

            num_chunks = len(chunks)
            if num_chunks > 1:
                await bot.send_message(chat_id,
                                       f"Длинное видео! Разделил на {num_chunks} чанков по 60 сек. Отправляю по одному... ✂️")

            for i, chunk_path in enumerate(chunks, 1):
                if num_chunks > 1:
                    await bot.send_message(chat_id, f"Подготавливаю чанк {i}/{num_chunks}...")

                processed_path = f"{chunk_path}_processed.mp4"
                if not await compress_video_if_needed(chunk_path, processed_path):
                    await bot.send_message(chat_id, f"Не удалось сжать чанк {i}. Пропускаю. 😔")
                    continue

                chunk_duration = await get_video_duration(processed_path)
                caption = f"Чанк {i}/{num_chunks} из Pornhub ({method_used}) | Длительность: {chunk_duration:.1f} сек"
                await send_with_retry(
                    bot.send_video,
                    chat_id,
                    video=types.FSInputFile(processed_path),
                    caption=caption,
                    supports_streaming=True
                )
                await asyncio.sleep(SLEEP_BETWEEN_CHUNKS)
                await cleanup_files(processed_path)  # Удаляем обработанный чанк после отправки

            await bot.send_message(chat_id, "Все чанки отправлены! Готово. 🎉")

    except Exception as e:
        logging.error(f"Error processing PH link: {e}")
        await bot.send_message(chat_id, "Общая ошибка при скачивании/обработке. ❌")
    finally:
        # cleanup_files(video_path) уже не нужен, так как используется tempfile
        shutil.rmtree(temp_dir, ignore_errors=True)
        await state.clear()


def register_ph_handlers(dp):
    dp.message.register(cmd_ph_download, Command("ph_v_d"))
    dp.message.register(process_ph_link, PHStates.waiting_for_link)