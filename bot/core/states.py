from aiogram.fsm.state import State, StatesGroup

class TikTokStates(StatesGroup):
    waiting_for_link = State()

class YouTubeStates(StatesGroup):
    waiting_for_link = State()

class PHStates(StatesGroup):
    waiting_for_link = State()

class ReelsStates(StatesGroup):
    waiting_for_link = State()

class AudioDownloadStates(StatesGroup):
    waiting_for_link = State()