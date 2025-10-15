import logging
from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from shazamio import Shazam
import yt_dlp
import os

from bot.core.states import AudioDownloadStates
from bot.utils.helpers import cleanup_files, download_with_retry, send_with_retry, validate_audio_file
from bot.utils.processing import run_ffmpeg_command, get_audio_duration


async def cmd_audio_download(message: types.Message, state: FSMContext):
    await message.answer("Отправьте ссылку на TikTok видео или Instagram Reel. Я извлеку аудио и отправлю MP3. 🎵")
    await state.set_state(AudioDownloadStates.waiting_for_link)

async def process_audio_link(message: types.Message, state: FSMContext):
    bot = message.bot
    await message.answer("Получил ссылку, скачиваю полностью... 🚀")
    link = message.text
    chat_id = message.chat.id
    video_path = f"./downloads/{chat_id}_audio_video.mp4"
    audio_path = f"./downloads/{chat_id}_audio_audio.mp3"

    try:
        # Скачивание видео с retry (как в tt/reels)
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
        extract_audio_cmd = f"ffmpeg -i {video_path} -vn -acodec libmp3lame -q:a 2 {audio_path}"
        _, stderr, returncode = await run_ffmpeg_command(extract_audio_cmd)
        if returncode != 0:
            logging.error(f"ffmpeg audio extraction error: {stderr.decode()}")
            await bot.send_message(chat_id, "Ошибка при извлечении аудио. 😔")
            return

        # Валидация аудио
        if not await validate_audio_file(audio_path):
            await bot.send_message(chat_id, "Извлеченное аудио не валидно. 😔")
            return

        # Shazam audio
        shazam = Shazam()
        out = await shazam.recognize_song(audio_path)
        track_info = "Не удалось распознать трек. 🤷‍♀️"
        if out and 'track' in out:
            title = out['track'].get('title', 'N/A')
            subtitle = out['track'].get('subtitle', 'N/A')
            track_info = f"🎵 Трек: {title} - {subtitle}"

        # Получаем длительность аудио
        duration = await get_audio_duration(audio_path)

        # Отправка аудио с retry
        await send_with_retry(
            bot.send_audio,
            chat_id,
            audio=types.FSInputFile(audio_path),
            caption=track_info,
            duration=int(duration)
        )

    except Exception as e:
        logging.error(f"Error processing audio link: {e}")
        await bot.send_message(chat_id, "Ошибка при скачивании или обработке. ❌")
    finally:
        await cleanup_files(video_path, audio_path, delay=1)
        await state.clear()

def register_audio_handlers(dp):
    dp.message.register(cmd_audio_download, Command("audio_download"))
    dp.message.register(process_audio_link, AudioDownloadStates.waiting_for_link)