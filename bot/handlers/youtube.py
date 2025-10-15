import logging
import re
from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
import yt_dlp
import os

from bot.core.states import YouTubeStates
from bot.utils.helpers import cleanup_files, download_with_retry, send_with_retry

async def cmd_youtube_download(message: types.Message, command: Command, state: FSMContext):
    quality = command.args if command.args else "480"
    await state.update_data(quality=quality)
    await message.answer(f"Отправьте ссылку на YouTube видео. Я скачаю его в качестве {quality}p. 🌟")
    await state.set_state(YouTubeStates.waiting_for_link)

async def process_youtube_link(message: types.Message, state: FSMContext):
    """Processes the YouTube link provided by the user."""
    bot = message.bot
    await message.answer("Получил ссылку, скачиваю полностью... 📥")
    link = message.text
    chat_id = message.chat.id
    user_data = await state.get_data()
    quality = user_data.get("quality", "480")
    video_path = f"./downloads/{chat_id}_youtube_video.mp4"

    try:
        ydl_opts = {
            'format': f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': video_path,
            'noplaylist': True,
        }
        downloaded_path = await download_with_retry(yt_dlp, ydl_opts, link)
        if not downloaded_path:
            await bot.send_message(chat_id, "Не удалось скачать видео после попыток. 😔")
            return
        video_path = downloaded_path

        await send_with_retry(
            bot.send_video,
            chat_id,
            video=types.FSInputFile(video_path),
            caption=f"Ваше YouTube видео в качестве {quality}p. 🎉"
        )

    except Exception as e:
        logging.error(f"Error processing YouTube link: {e}")
        await bot.send_message(chat_id, "Ошибка при скачивании YouTube видео. ❌")
    finally:
        await cleanup_files(video_path, delay=1)
        await state.clear()

def register_youtube_handlers(dp):
    dp.message.register(cmd_youtube_download, Command(re.compile(r"yt_v_d(\d*)")))
    dp.message.register(process_youtube_link, YouTubeStates.waiting_for_link)