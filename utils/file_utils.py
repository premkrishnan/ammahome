# ============================================================
# FILE: utils/file_utils.py
#
# PURPOSE:
#   Shared helper functions for managing temporary media files.
#   Handles creating unique file paths, cleaning up temp files
#   after they are sent to the display, and converting media
#   to base64 for WebSocket transmission.
#
# INPUTS:
#   - File paths, raw bytes, or message IDs
#
# OUTPUTS:
#   - pathlib.Path objects for temp files
#   - base64 encoded strings for WebSocket payloads
#
# DEPENDENCIES:
#   - Python standard library: pathlib, base64, os, uuid
#   - config.py → TEMP_DIR
#
# CALLED BY:
#   - services/media_handler.py
#   - services/display_server.py
#   - services/tts.py
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import base64
import uuid
from pathlib import Path

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def make_temp_path(media_type: str, extension: str) -> Path:
    """
    Creates a unique file path inside the temp/ directory.

    Steps:
      1. Generate a short unique ID using uuid4
      2. Build the filename as: {media_type}_{unique_id}.{extension}
      3. Return the full path inside TEMP_DIR

    Args:
        media_type (str): Type label for the file. Example: "photo", "voice", "video"
        extension (str):  File extension without dot. Example: "jpg", "ogg", "mp4"

    Returns:
        Path: A unique path that does not yet exist on disk.
              Example: Path("temp/photo_3f2a1b.jpg")

    Example:
        path = make_temp_path("voice", "ogg")
        # Returns something like: temp/voice_a1b2c3d4.ogg
    """
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{media_type}_{unique_id}.{extension}"
    return config.TEMP_DIR / filename


def read_as_base64(file_path: Path) -> str | None:
    """
    Reads a file from disk and returns it as a base64-encoded string.

    Steps:
      1. Check that the file exists
      2. Read the file as raw bytes
      3. Encode the bytes to base64
      4. Return as a UTF-8 string

    Args:
        file_path (Path): Full path to the file to encode.
                          Example: Path("temp/photo_a1b2c3.jpg")

    Returns:
        str:  Base64-encoded file contents as a UTF-8 string.
        None: If the file does not exist or cannot be read.

    Example:
        encoded = read_as_base64(Path("temp/voice_abc.ogg"))
        if encoded:
            payload["data"] = encoded
    """
    if not file_path.exists():
        logger.error(f"Cannot encode file — not found: {file_path}")
        return None

    try:
        raw_bytes = file_path.read_bytes()
        encoded = base64.b64encode(raw_bytes).decode("utf-8")
        logger.debug(f"Encoded {file_path.name} to base64 ({len(raw_bytes)} bytes)")
        return encoded
    except OSError as error:
        logger.error(f"Failed to read file {file_path}: {error}")
        return None


def delete_temp_file(file_path: Path) -> None:
    """
    Deletes a temporary media file from disk after it has been sent.

    Steps:
      1. Check that the file exists
      2. Delete it
      3. Log success or skip silently if already gone

    Args:
        file_path (Path): Full path to the temp file to delete.
                          Example: Path("temp/photo_a1b2c3.jpg")

    Returns:
        None

    Example:
        delete_temp_file(Path("temp/voice_abc.ogg"))
        # File is removed; temp/ stays clean
    """
    if not file_path.exists():
        # Already gone — nothing to do
        return

    try:
        file_path.unlink()
        logger.debug(f"Deleted temp file: {file_path.name}")
    except OSError as error:
        logger.warning(f"Could not delete temp file {file_path.name}: {error}")


def clear_all_temp_files() -> int:
    """
    Deletes all files inside the temp/ directory.

    Steps:
      1. List all files in TEMP_DIR
      2. Delete each one
      3. Return the count of files deleted

    Args:
        None

    Returns:
        int: Number of files deleted. Example: 3

    Example:
        count = clear_all_temp_files()
        logger.info(f"Cleared {count} temp files on startup")
    """
    deleted_count = 0

    for temp_file in config.TEMP_DIR.iterdir():
        # Skip .gitkeep — it keeps the temp/ folder tracked in git
        if temp_file.name == ".gitkeep":
            continue

        try:
            temp_file.unlink()
            deleted_count += 1
        except OSError as error:
            logger.warning(f"Could not delete {temp_file.name}: {error}")

    if deleted_count > 0:
        logger.info(f"Cleared {deleted_count} leftover temp files from previous run")

    return deleted_count
