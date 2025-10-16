import asyncio
import logging
import tempfile
import shutil
import re
import json
from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
import yt_dlp
import youtube_dl
import requests
from bs4 import BeautifulSoup
import os

from bot.core.states import PHStates
from bot.utils.helpers import send_with_retry

async def cmd_ph_download(message: types.Message, state: FSMContext):
    await message.answer("Отправьте ссылку на Pornhub видео. Я скачаю и отправлю полное видео или ссылку. 🔥")
    await state.set_state(PHStates.waiting_for_link)


async def process_ph_link(message: types.Message, state: FSMContext):
    bot = message.bot
    await message.answer("Получил ссылку, скачиваю полностью... 📥")
    link = message.text
    chat_id = message.chat.id
    temp_dir = tempfile.mkdtemp()
    video_path = None
    method_used = ""

    try:
        # Метод 1: yt-dlp
        try:
            await bot.send_message(chat_id, "Пытаюсь скачать через yt-dlp... 🔧")
            video_path_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': video_path_template,
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                video_path = ydl.prepare_filename(info)
                if os.path.exists(video_path) and os.path.getsize(video_path) > 10240:
                    method_used = "yt-dlp"
                    await bot.send_message(chat_id, f"Скачано с {method_used}! Отправляю видео... ✅")
                else:
                    video_path = None
        except Exception as e:
            logging.warning(f"yt-dlp failed: {e}")
            video_path = None

        # Метод 2: youtube-dl (fallback)
        if not video_path:
            try:
                await bot.send_message(chat_id, "Пытаюсь скачать через youtube-dl (fallback)... 🔧")
                video_path_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                    'outtmpl': video_path_template,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=True)
                    video_path = ydl.prepare_filename(info)
                    if os.path.exists(video_path) and os.path.getsize(video_path) > 10240:
                        method_used = "youtube-dl"
                        await bot.send_message(chat_id, f"Скачано с {method_used}! Отправляю видео... ✅")
                    else:
                        video_path = None
            except Exception as e:
                logging.warning(f"youtube-dl failed: {e}")
                video_path = None

        # Метод 3: Прямой парсинг (direct parsing)
        if not video_path:
            try:
                await bot.send_message(chat_id, "Пытаюсь получить прямую ссылку через парсинг... 🔗")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(link, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                # Найти скрипт с данными о видео
                player_config_script = soup.find('script', text=re.compile('flashvars'))
                if player_config_script:
                    player_config_str = player_config_script.string
                    # Извлечь JSON часть
                    match = re.search(r'var flashvars[^=]*=\s*(\{.*?\});', player_config_str, re.DOTALL)
                    if match:
                        flashvars_json = match.group(1)
                        flashvars = json.loads(flashvars_json)

                        # Извлечь ссылки на видео
                        media_definitions = flashvars.get('mediaDefinitions', [])
                        video_urls = []
                        for media_def in media_definitions:
                            if media_def.get('videoUrl'):
                                video_urls.append(media_def['videoUrl'])
                            elif media_def.get('quality'):
                                # Иногда ссылки находятся в другом формате
                                for quality_item in media_def.get('quality', []):
                                    if quality_item.get('videoUrl'):
                                        video_urls.append(quality_item['videoUrl'])

                        if video_urls:
                            # Возвращаем самую качественную (последнюю) ссылку
                            direct_link = video_urls[-1]
                            method_used = "direct_parsing"
                            await bot.send_message(chat_id, f"Нашел прямую ссылку через {method_used}! 🎉\n\n{direct_link}")
                            return

                await bot.send_message(chat_id, "Не удалось найти прямую ссылку через парсинг. 😔")
            except Exception as e:
                logging.warning(f"Direct parsing failed: {e}")

        # Если ничего не сработало
        if not video_path:
            await bot.send_message(chat_id,
                                   "Не удалось скачать ни одним методом после попыток. Попробуй другую ссылку. ❌")
            return

        # Отправляем полное видео
        await send_with_retry(
            bot.send_video,
            chat_id,
            video=types.FSInputFile(video_path),
            caption=f"Видео с Pornhub ({method_used})",
            supports_streaming=True
        )
        await bot.send_message(chat_id, "Видео отправлено! Готово. 🎉")

    except Exception as e:
        logging.error(f"Error processing PH link: {e}")
        await bot.send_message(chat_id, "Общая ошибка при скачивании/обработке. ❌")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        await state.clear()


def register_ph_handlers(dp):
    dp.message.register(cmd_ph_download, Command("ph_v_d"))
    dp.message.register(process_ph_link, PHStates.waiting_for_link)

