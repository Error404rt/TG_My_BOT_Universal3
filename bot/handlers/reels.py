import logging
import shlex
from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from shazamio import Shazam
import yt_dlp
import os

from bot.core.states import ReelsStates
from bot.utils.helpers import cleanup_files, download_with_retry, send_with_retry
from bot.utils.processing import run_ffmpeg_command

async def cmd_reels_download(message: types.Message, state: FSMContext):
    await message.answer("Отправьте ссылку на Instagram Reel. 📸")
    await state.set_state(ReelsStates.waiting_for_link)

async def process_reels_link(message: types.Message, state: FSMContext):
    bot = message.bot
    await message.answer("Получил ссылку, скачиваю полностью... 🚀")
    link = message.text
    chat_id = message.chat.id
    video_path = f"./downloads/{chat_id}_reels_video.mp4"
    audio_path = f"./downloads/{chat_id}_reels_audio.mp3"

    try:
        # Скачивание с retry
        ydl_opts = {
            'format': 'best[ext=mp4]',
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
        extract_audio_cmd = f"ffmpeg -i {shlex.quote(video_path)} -vn -acodec libmp3lame -q:a 2 {shlex.quote(audio_path)}"
        _, stderr, returncode = await run_ffmpeg_command(extract_audio_cmd)
        if returncode != 0:
            logging.error(f"ffmpeg audio extraction error: {stderr.decode()}")
            await bot.send_message(chat_id, "Ошибка при извлечении аудио. 😔")
            return

        # Shazam audio
        track_info = "Не удалось распознать трек. 🤷‍♀️"
        try:
            shazam = Shazam()
            out = await shazam.recognize(audio_path)
            if out and 'track' in out:
                title = out['track'].get('title', 'N/A')
                subtitle = out['track'].get('subtitle', 'N/A')
                track_info = f"🎵 Трек: {title} - {subtitle}"
        except Exception as e:
            logging.warning(f"Shazam recognition failed: {e}")

        # Отправка с retry
        await send_with_retry(
            bot.send_video,
            chat_id,
            video=types.FSInputFile(video_path),
            caption=track_info
        )

    except Exception as e:
        logging.error(f"Error processing Reels link: {e}")
        await bot.send_message(chat_id, "Ошибка при скачивании или обработке Instagram Reel. ❌")
    finally:
        await cleanup_files(video_path, audio_path, delay=1)
        await state.clear()

def register_reels_handlers(dp):
    dp.message.register(cmd_reels_download, Command("reels_v_d"))
    dp.message.register(process_reels_link, ReelsStates.waiting_for_link)