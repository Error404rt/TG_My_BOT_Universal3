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
        # 1. Получение информации о посте
        await bot.send_message(chat_id, "Получил ссылку, анализирую пост... 🧐")
        
        ydl_opts_info = {
            'skip_download': True,
            'quiet': True,
            'force_generic_extractor': True,
        }
        
        info_extractor = yt_dlp.YoutubeDL(ydl_opts_info)
        info = None
        try:
            info = info_extractor.extract_info(link, download=False)
        except Exception as e:
            logging.error(f"yt-dlp info extraction error: {e}")
            await bot.send_message(chat_id, "Не удалось получить информацию о посте. Возможно, ссылка неверна или пост приватный. 😔")
            return

        # 2. Определение типа контента и получение ссылки
        download_url = None
        file_type = None
        is_video = False
        
        if info.get('_type') == 'playlist' and 'entries' in info:
            # Это может быть карусель. Берем первый элемент.
            first_entry = info['entries'][0]
            if first_entry.get('ext') in ['mp4', 'webm']:
                is_video = True
                download_url = first_entry.get('url')
                file_type = 'video'
            elif first_entry.get('ext') in ['jpg', 'jpeg', 'png']:
                download_url = first_entry.get('url')
                file_type = 'photo'
        elif info.get('ext') in ['mp4', 'webm']:
            # Это видео (Reel или обычное видео)
            is_video = True
            download_url = info.get('url')
            file_type = 'video'
        elif info.get('ext') in ['jpg', 'jpeg', 'png']:
            # Это изображение
            download_url = info.get('url')
            file_type = 'photo'
        
        if not download_url:
            await bot.send_message(chat_id, "Не удалось найти прямую ссылку для скачивания. Пост может содержать неподдерживаемый контент. 😔")
            return

        # 3. Обработка в зависимости от типа контента
        if file_type == 'photo':
            await bot.send_message(chat_id, "Нашел изображение! Вот прямая ссылка для скачивания: 👇")
            await bot.send_message(chat_id, download_url)
            # Отправка самого изображения для удобства
            try:
                # types.URLInputFile требует aiogram 3.x, если у вас aiogram 2.x, то нужно будет использовать requests для скачивания и types.InputFile
                await send_with_retry(
                    bot.send_photo,
                    chat_id,
                    photo=types.URLInputFile(download_url),
                    caption="Прямая ссылка выше 👆"
                )
            except Exception as e:
                logging.warning(f"Could not send photo directly: {e}")
                await bot.send_message(chat_id, "Не удалось отправить изображение напрямую, но ссылка рабочая. 🖼️")
            
        elif file_type == 'video':
            await bot.send_message(chat_id, "Нашел видео (Reel)! Скачиваю и обрабатываю... 🚀")
            
            # Скачивание видео
            ydl_opts_download = {
                'format': 'best[ext=mp4]',
                'outtmpl': video_path,
                'noplaylist': True,
            }
            downloaded_path = await download_with_retry(yt_dlp, ydl_opts_download, link)
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
                # Продолжаем без Shazam, чтобы отправить хотя бы видео
                track_info = "Не удалось извлечь аудио для Shazam. 🤷‍♀️"
            else:
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
        
        # Если это не фото и не видео, то ничего не делаем, сообщение об ошибке уже было выше.

    except Exception as e:
        logging.error(f"Error processing Reels link: {e}")
        await bot.send_message(chat_id, "Ошибка при скачивании или обработке Instagram Reel. ❌")
    finally:
        await cleanup_files(video_path, audio_path, delay=1)
        await state.clear()

def register_reels_handlers(dp):
    dp.message.register(cmd_reels_download, Command("reels_v_d"))
    dp.message.register(process_reels_link, ReelsStates.waiting_for_link)
