# ============================================================
# FILE: services/media_handler.py
#
# PURPOSE:
#   Downloads media files (photos, videos, voice messages)
#   from Telegram servers to the local temp/ directory.
#   Returns the local file path so the display server can
#   read and send the file to the iPad.
#
# INPUTS:
#   - Telegram File objects from python-telegram-bot
#   - media_type label string ("photo", "video", "voice")
#   - file extension string ("jpg", "mp4", "ogg")
#
# OUTPUTS:
#   - pathlib.Path to the downloaded file in temp/
#   - None if download fails
#
# DEPENDENCIES:
#   - python-telegram-bot (pip install python-telegram-bot)
#   - config.py → TEMP_DIR
#   - utils/logger.py
#   - utils/file_utils.py → make_temp_path, delete_temp_file
#
# CALLED BY:
#   - services/bot.py → handle_photo, handle_video, handle_voice
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

from pathlib import Path

from telegram import File

import config
from utils.file_utils import make_temp_path
from utils.logger import get_logger

logger = get_logger(__name__)


async def download_photo(telegram_file: File) -> Path | None:
    """
    Downloads a photo from Telegram to the temp/ directory.

    Steps:
      1. Create a unique temp file path with .jpg extension
      2. Download the file from Telegram servers
      3. Log success with file size
      4. Return the local path

    Args:
        telegram_file (File): Telegram File object from get_file().
                              Example: await context.bot.get_file(photo.file_id)

    Returns:
        Path: Local path to the downloaded photo.
              Example: Path("temp/photo_a1b2c3d4.jpg")
        None: If the download fails.

    Example:
        local_path = await download_photo(tg_file)
        if local_path:
            await push_photo_to_display(local_path, sender_name)
    """
    local_path = make_temp_path("photo", "jpg")

    try:
        await telegram_file.download_to_drive(local_path)
        file_size_kb = local_path.stat().st_size // 1024
        logger.info(f"Photo downloaded to {local_path.name} ({file_size_kb} KB)")
        return local_path
    except Exception as error:
        logger.error(f"Failed to download photo: {error}")
        logger.error("Fix: Check internet connection and Telegram bot token")
        return None


async def download_video(telegram_file: File) -> Path | None:
    """
    Downloads a video from Telegram to the temp/ directory.

    Steps:
      1. Create a unique temp file path with .mp4 extension
      2. Download the file from Telegram servers
      3. Log success with file size
      4. Return the local path

    Args:
        telegram_file (File): Telegram File object from get_file().
                              Example: await context.bot.get_file(video.file_id)

    Returns:
        Path: Local path to the downloaded video.
              Example: Path("temp/video_b2c3d4e5.mp4")
        None: If the download fails.

    Example:
        local_path = await download_video(tg_file)
        if local_path:
            await push_video_to_display(local_path, sender_name)
    """
    local_path = make_temp_path("video", "mp4")

    try:
        await telegram_file.download_to_drive(local_path)
        file_size_kb = local_path.stat().st_size // 1024
        logger.info(f"Video downloaded to {local_path.name} ({file_size_kb} KB)")
        return local_path
    except Exception as error:
        logger.error(f"Failed to download video: {error}")
        logger.error("Fix: Check internet connection and Telegram bot token")
        return None


async def download_voice(telegram_file: File) -> Path | None:
    """
    Downloads a voice message from Telegram to the temp/ directory.

    Steps:
      1. Create a unique temp file path with .ogg extension
      2. Download the file from Telegram servers
      3. Log success with file size
      4. Return the local path

    Args:
        telegram_file (File): Telegram File object from get_file().
                              Example: await context.bot.get_file(voice.file_id)

    Returns:
        Path: Local path to the downloaded voice file.
              Example: Path("temp/voice_c3d4e5f6.ogg")
        None: If the download fails.

    Example:
        local_path = await download_voice(tg_file)
        if local_path:
            await push_voice_to_display(local_path, sender_name)
    """
    local_path = make_temp_path("voice", "ogg")

    try:
        await telegram_file.download_to_drive(local_path)
        file_size_kb = local_path.stat().st_size // 1024
        logger.info(f"Voice downloaded to {local_path.name} ({file_size_kb} KB)")
        return local_path
    except Exception as error:
        logger.error(f"Failed to download voice message: {error}")
        logger.error("Fix: Check internet connection and Telegram bot token")
        return None


def get_sender_name(user_id: int) -> str:
    """
    Looks up a friendly display name for a Telegram user ID.

    Steps:
      1. Convert user_id to string (config keys are strings)
      2. Look up in FAMILY_MEMBER_NAMES from config
      3. Return the name if found, or "Family" as a safe fallback

    Args:
        user_id (int): Telegram user ID of the message sender.
                       Example: 123456789

    Returns:
        str: Display name for the sender.
             Example: "Prem" if mapped, or "Family" if unknown.

    Example:
        name = get_sender_name(update.message.from_user.id)
        # Returns "Prem" or "Family"
    """
    name = config.FAMILY_MEMBER_NAMES.get(str(user_id), "Family")
    return name


def build_message_id(sender_id: int, telegram_message_id: int) -> str:
    """
    Builds a unique message ID string for WebSocket tracking.

    Steps:
      1. Combine sender_id and telegram_message_id with underscore
      2. Return as a string

    Args:
        sender_id (int):           Telegram user ID. Example: 123456789
        telegram_message_id (int): Telegram message ID. Example: 42

    Returns:
        str: Unique message ID. Example: "123456789_42"

    Example:
        msg_id = build_message_id(update.message.from_user.id,
                                  update.message.message_id)
        # Returns "123456789_42"
    """
    return f"{sender_id}_{telegram_message_id}"
