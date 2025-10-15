import asyncio
import logging
from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from shazamio import Shazam
import yt_dlp
import os

from bot.core.states import TikTokStates
from bot.utils.helpers import cleanup_files, download_with_retry, send_with_retry
from bot.utils.processing import run_ffmpeg_command

# --- TikTok Downloader Feature ---
async def cmd_tiktok_download(message: types.Message, state: FSMContext):
    """Handles the /tt_v_d command to start the TikTok download process."""
    await message.answer("Отправьте ссылку на TikTok видео. 🎶")
    await state.set_state(TikTokStates.waiting_for_link)

async def process_tiktok_link(message: types.Message, state: FSMContext):
    """Processes the TikTok link provided by the user."""
    bot = message.bot
    await message.answer("Получил ссылку, скачиваю полностью... 🚀")
    link = message.text
    chat_id = message.chat.id
    # Используем tempfile или фиксированную папку
    video_path = f"./downloads/{chat_id}_tiktok_video.mp4"
    audio_path = f"./downloads/{chat_id}_tiktok_audio.mp3"

    try:
        # Скачивание с retry
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': video_path,
            'noplaylist': True,
        }
        downloaded_path = await download_with_retry(yt_dlp, ydl_opts, link)
        if not downloaded_path:
            await bot.send_message(chat_id, "Не удалось скачать видео после попыток. 😔")
            return
        video_path = downloaded_path

        await bot.send_message(chat_id, "Видео скачано, обрабатываю аудио для Shazam... 🎧")

        # Extract audio
        extract_audio_cmd = f"ffmpeg -i {video_path} -vn -acodec libmp3lame -q:a 2 {audio_path}"
        _, stderr, returncode = await run_ffmpeg_command(extract_audio_cmd)
        if returncode != 0:
            logging.error(f"ffmpeg audio extraction error: {stderr.decode()}")
            await bot.send_message(chat_id, "Ошибка при извлечении аудио. 😔")
            return

        # Shazam audio
        shazam = Shazam()
        out = await shazam.recognize_song(audio_path)
        track_info = "Не удалось распознать трек. 🤷‍♀️"
        if out and 'track' in out:
            title = out['track'].get('title', 'N/A')
            subtitle = out['track'].get('subtitle', 'N/A')
            track_info = f"🎵 Трек: {title} - {subtitle}"

        # Отправка с retry
        await send_with_retry(
            bot.send_video,
            chat_id,
            video=types.FSInputFile(video_path),
            caption=track_info
        )

    except Exception as e:
        logging.error(f"Error processing TikTok link: {e}")
        await bot.send_message(chat_id, "Ошибка при скачивании или обработке TikTok видео. ❌")
    finally:
        await cleanup_files(video_path, audio_path, delay=1)
        await state.clear()

def register_tiktok_handlers(dp):
    dp.message.register(cmd_tiktok_download, Command("tt_v_d"))
    dp.message.register(process_tiktok_link, TikTokStates.waiting_for_link)