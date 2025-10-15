from decouple import config

BOT_TOKEN = config('BOT_TOKEN', default='your-api-token')

MAX_DURATION_SECONDS = config('MAX_DURATION_SECONDS', default=60, cast=int)
MAX_FILE_SIZE_BYTES = config('MAX_FILE_SIZE_BYTES', default=12582912, cast=int)
MAX_VIDEO_SIZE_BYTES = config('MAX_VIDEO_SIZE_BYTES', default=52428800, cast=int)
CIRCLE_SIZE = config('CIRCLE_SIZE', default=640, cast=int)
MIN_FILE_SIZE_BYTES = config('MIN_FILE_SIZE_BYTES', default=10240, cast=int)
RETRY_DOWNLOAD_ATTEMPTS = config('RETRY_DOWNLOAD_ATTEMPTS', default=2, cast=int)
RETRY_SEND_ATTEMPTS = config('RETRY_SEND_ATTEMPTS', default=3, cast=int)
SLEEP_BETWEEN_CHUNKS = config('SLEEP_BETWEEN_CHUNKS', default=2, cast=int)