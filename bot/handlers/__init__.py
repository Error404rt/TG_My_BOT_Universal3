from .start import register_start_handlers
from .video_circle import register_video_circle_handlers
from .tiktok import register_tiktok_handlers
from .youtube import register_youtube_handlers
from .pornhub import register_ph_handlers
from .reels import register_reels_handlers
from .audio_download import register_audio_handlers
from .image_converter import router as image_converter_router

from aiogram import Dispatcher, Bot


def register_all_handlers(dp: Dispatcher, bot: Bot):
    register_start_handlers(dp)

    register_video_circle_handlers(dp, bot)

    register_tiktok_handlers(dp)
    register_youtube_handlers(dp)
    register_ph_handlers(dp)
    register_reels_handlers(dp)
    register_audio_handlers(dp)
    
    dp.include_router(image_converter_router)