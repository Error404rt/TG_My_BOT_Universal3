import asyncio
import logging
import os
import shutil
import shlex

from bot.core.config import MAX_DURATION_SECONDS, MAX_VIDEO_SIZE_BYTES, MAX_FILE_SIZE_BYTES, CIRCLE_SIZE
from bot.utils.helpers import validate_video_file


async def check_ffmpeg_installed() -> bool:
    """Проверяет, установлен ли FFmpeg/FFprobe и доступен ли в PATH."""
    try:
        command = "ffmpeg -version"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        returncode = process.returncode

        if returncode == 0:
            logging.info("FFmpeg/FFprobe успешно найдены в системе.")
            return True
        else:
            logging.error(f"FFmpeg/FFprobe не найдены или произошла ошибка. Код возврата: {returncode}")
            return False

    except FileNotFoundError:
        logging.error("FFmpeg/FFprobe не найдены. Убедитесь, что они установлены и прописаны в PATH.")
        return False
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при проверке FFmpeg: {e}")
        return False


async def run_ffmpeg_command(command: str) -> tuple[bytes, bytes, int]:
    """Runs an FFmpeg command and returns stdout, stderr, and return code."""
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout, stderr, process.returncode


async def get_video_duration(video_path: str) -> float:
    """Получает длительность видео с помощью ffprobe."""
    duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(video_path)}"
    stdout, stderr, returncode = await run_ffmpeg_command(duration_cmd)
    if returncode != 0:
        logging.error(f"ffprobe error: {stderr.decode()}")
        return 0
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0


async def get_audio_duration(audio_path: str) -> float:
    """Получает длительность аудио с помощью ffprobe."""
    duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(audio_path)}"
    stdout, stderr, returncode = await run_ffmpeg_command(duration_cmd)
    if returncode != 0:
        logging.error(f"ffprobe error: {stderr.decode()}")
        return 0
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0


async def split_video_chunks(input_path: str, chunk_dir: str, max_duration=MAX_DURATION_SECONDS) -> list[str]:
    """Разделяет видео на чанки по max_duration секунд с помощью FFmpeg и валидацией."""
    duration = await get_video_duration(input_path)
    if duration <= max_duration:
        output_path = os.path.join(chunk_dir, 'chunk_001.mp4')
        shutil.copy2(input_path, output_path)
        if await validate_video_file(output_path):
            return [output_path]
        return []

    os.makedirs(chunk_dir, exist_ok=True)
    cmd = f"ffmpeg -i {shlex.quote(input_path)} -c copy -map 0 -segment_time {max_duration} -f segment -reset_timestamps 1 {shlex.quote(chunk_dir)}/chunk_%03d.mp4"
    _, stderr, returncode = await run_ffmpeg_command(cmd)
    if returncode != 0:
        logging.error(f"ffmpeg split error: {stderr.decode()}")
        return []

    valid_chunks = []
    chunks = sorted([f for f in os.listdir(chunk_dir) if f.endswith('.mp4')])
    for chunk in chunks:
        chunk_path = os.path.join(chunk_dir, chunk)
        if await validate_video_file(chunk_path):
            valid_chunks.append(chunk_path)
        else:
            # Очистка невалидного чанка не нужна, т.к. очищается весь chunk_dir
            pass
    return valid_chunks


async def compress_video_if_needed(input_path: str, output_path: str, max_size=MAX_VIDEO_SIZE_BYTES):
    """Сжимает видео, если оно больше max_size, с валидацией."""
    file_size = os.path.getsize(input_path)
    if file_size <= max_size:
        shutil.copy2(input_path, output_path)
        return await validate_video_file(output_path)

    # Сжатие с первым проходом
    cmd = (
        f"ffmpeg -i {shlex.quote(input_path)} "
        f"-vf scale=-2:720 "
        f"-c:v libx264 -crf 28 -c:a aac -b:a 128k "
        f"{shlex.quote(output_path)}"
    )
    _, stderr, returncode = await run_ffmpeg_command(cmd)
    if returncode != 0:
        logging.error(f"ffmpeg compress error: {stderr.decode()}")
        return False

    # Проверка и агрессивное сжатие
    new_size = os.path.getsize(output_path)
    if new_size > max_size:
        cmd2 = (
            f"ffmpeg -i {shlex.quote(output_path)} "
            f"-vf scale=-2:480 "
            f"-c:v libx264 -crf 32 -c:a aac -b:a 64k "
            f"{shlex.quote(output_path)}.temp.mp4"
        )
        await run_ffmpeg_command(cmd2)
        os.replace(f"{output_path}.temp.mp4", output_path)
        new_size = os.path.getsize(output_path)
        if new_size > max_size:
            logging.warning(f"Video still too large: {new_size} bytes")
            return False

    return await validate_video_file(output_path)


async def process_video_to_circle(input_path: str, chat_id: int, bot):
    """Обрабатывает видео-чанк в кружок с помощью FFmpeg, сжимает до <12 МБ, с валидацией."""
    from aiogram import types  # Локальный импорт
    from bot.utils.helpers import cleanup_files, send_with_retry  # Локальный импорт

    output_path = f"{input_path}_circle.mp4"
    try:
        # Основная команда: crop в квадрат, scale, pad, compress
        cmd_crop = (
            f"ffmpeg -i {shlex.quote(input_path)} "
            f"-vf 'crop=min(iw\\,ih):min(iw\\,ih),scale={CIRCLE_SIZE}:{CIRCLE_SIZE}:force_original_aspect_ratio=decrease,pad={CIRCLE_SIZE}:{CIRCLE_SIZE}:(ow-iw)/2:(oh-ih)/2:black,setsar=1' "
            f"-c:v libx264 -crf 28 -c:a aac -b:a 64k -t {MAX_DURATION_SECONDS} "
            f"-pix_fmt yuv420p -movflags +faststart {shlex.quote(output_path)}"
        )
        _, stderr, returncode = await run_ffmpeg_command(cmd_crop)
        if returncode != 0:
            logging.error(f"ffmpeg crop error: {stderr.decode()}")
            await bot.send_message(chat_id, "Ошибка при создании кружка. 😭")
            return

        # Проверка и сжатие
        final_size = os.path.getsize(output_path)
        if final_size > MAX_FILE_SIZE_BYTES:
            logging.warning(f"File too large: {final_size} bytes. Compressing further.")
            temp_path = f"{output_path}.temp.mp4"
            cmd_compress = (
                f"ffmpeg -i {shlex.quote(output_path)} "
                f"-vf scale=480:480 "
                f"-c:v libx264 -crf 32 -c:a aac -b:a 48k "
                f"{shlex.quote(temp_path)}"
            )
            _, stderr, returncode = await run_ffmpeg_command(cmd_compress)
            if returncode != 0:
                logging.error(f"ffmpeg compress error: {stderr.decode()}")
                await bot.send_message(chat_id, "Не удалось сжать видео до нужного размера. Попробуйте короче видео. 😔")
                return
            os.replace(temp_path, output_path)
            final_size = os.path.getsize(output_path)
            if final_size > MAX_FILE_SIZE_BYTES:
                await bot.send_message(chat_id, f"Видео всё ещё слишком большое ({final_size // 1024 // 1024} МБ). 😔")
                return

        if not await validate_video_file(output_path):
            await bot.send_message(chat_id, "Обработанный кружок не валиден. 😔")
            return

        duration = await get_video_duration(output_path)

        await send_with_retry(
            bot.send_video_note,
            chat_id=chat_id,
            video_note=types.FSInputFile(output_path),
            duration=int(duration),
            length=CIRCLE_SIZE
        )

    except Exception as e:
        logging.error(f"Error processing video to circle: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при создании кружка. 😭")
    finally:
        await cleanup_files(output_path, delay=1)