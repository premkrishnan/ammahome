# ============================================================
# FILE: services/bot.py
#
# PURPOSE:
#   Connects to Telegram, monitors the family group chat,
#   and forwards all incoming messages (photo, video, voice,
#   text) to the display server to show on Amma's iPad.
#   Also handles voice notes sent back from Amma and
#   forwards them to the family group.
#
# INPUTS:
#   - Telegram group messages: photos, videos, voice, text
#   - Voice reply payloads from the display server (Amma's voice)
#
# OUTPUTS:
#   - Calls display_server.push_to_display() for each message
#   - Sends acknowledgement "Amma saw it ❤️" back to family group
#   - Forwards Amma's voice notes to the family group
#
# DEPENDENCIES:
#   - python-telegram-bot (pip install python-telegram-bot)
#   - config.py → TELEGRAM_BOT_TOKEN, FAMILY_GROUP_CHAT_ID
#   - services/media_handler.py → download helpers, get_sender_name
#   - services/display_server.py → DisplayServer (passed in)
#   - services/tts.py → text_to_speech_file
#   - utils/logger.py
#
# CALLED BY:
#   - main.py → run_bot(display_server)
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import asyncio
import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from services.media_handler import (
    build_message_id,
    download_photo,
    download_video,
    download_voice,
    get_sender_name,
)
from services.tts import text_to_speech_file
from utils.file_utils import delete_temp_file, read_as_base64
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Module-level bot application instance ────────────────────
# Stored here so send_voice_to_group() can use it from outside
_bot_app: Application | None = None


def get_bot_app() -> Application | None:
    """
    Returns the running Telegram bot Application instance.

    Steps:
      1. Return the module-level _bot_app if set
      2. Return None if the bot has not started yet

    Args:
        None

    Returns:
        Application: The running bot instance, or None if not started.

    Example:
        app = get_bot_app()
        if app:
            await app.bot.send_message(chat_id=group_id, text="Hello")
    """
    return _bot_app


async def send_ack_to_group(context: ContextTypes.DEFAULT_TYPE, sender_name: str) -> None:
    """
    Sends an acknowledgement message to the family Telegram group.

    Steps:
      1. Build the acknowledgement text with sender name
      2. Send to FAMILY_GROUP_CHAT_ID
      3. Log success or failure

    Args:
        context (ContextTypes.DEFAULT_TYPE): Telegram bot context.
        sender_name (str): Name of who sent the original message.
                           Example: "Prem"

    Returns:
        None

    Example:
        await send_ack_to_group(context, "Prem")
        # Sends "Amma saw Prem's message ❤️" to family group
    """
    ack_text = f"Amma saw {sender_name}'s message ❤️"

    try:
        await context.bot.send_message(
            chat_id=config.FAMILY_GROUP_CHAT_ID,
            text=ack_text,
        )
        logger.info(f"Acknowledgement sent to family group: {ack_text}")
    except Exception as error:
        logger.error(f"Failed to send acknowledgement to group: {error}")
        logger.error("Fix: Check FAMILY_GROUP_CHAT_ID in .env and bot group membership")


async def send_amma_voice_to_group(voice_file_path: Path) -> None:
    """
    Sends Amma's voice note to the family Telegram group.

    Steps:
      1. Check the bot is running
      2. Open the voice file from disk
      3. Send it as a voice message to the family group
      4. Log success or failure

    Args:
        voice_file_path (Path): Path to Amma's recorded voice file.
                                Example: Path("temp/amma_voice_a1b2c3.ogg")

    Returns:
        None

    Example:
        await send_amma_voice_to_group(Path("temp/amma_voice_abc.ogg"))
        # Family receives a voice note from Amma in the group
    """
    if _bot_app is None:
        logger.error("Cannot send Amma's voice — bot not running yet")
        return

    if not voice_file_path.exists():
        logger.error(f"Cannot send Amma's voice — file not found: {voice_file_path}")
        return

    try:
        with open(voice_file_path, "rb") as voice_file:
            await _bot_app.bot.send_voice(
                chat_id=config.FAMILY_GROUP_CHAT_ID,
                voice=voice_file,
                caption="🎙️ Amma sent a voice message",
            )
        logger.info("Amma's voice note sent to family group")
    except Exception as error:
        logger.error(f"Failed to send Amma's voice to group: {error}")
        logger.error("Fix: Check FAMILY_GROUP_CHAT_ID and bot permissions")
    finally:
        # Clean up Amma's temp voice file after sending
        delete_temp_file(voice_file_path)


def _build_payload(
    message_type: str,
    sender_name: str,
    message_id: str,
    data: str,
    mime_type: str | None = None,
) -> dict:
    """
    Builds the JSON payload to send to the display server.

    Steps:
      1. Assemble all fields into a dictionary
      2. Include current timestamp in ISO format
      3. Return the payload dict

    Args:
        message_type (str): Type of content. Example: "photo", "voice", "text"
        sender_name (str):  Display name of sender. Example: "Prem"
        message_id (str):   Unique ID for this message. Example: "123_42"
        data (str):         Base64 media or plain text. Example: "/9j/4AAQ..."
        mime_type (str):    MIME type for media, or None for text.
                            Example: "image/jpeg"

    Returns:
        dict: Complete payload ready to send via WebSocket.

    Example:
        payload = _build_payload("photo", "Prem", "123_42", base64_str, "image/jpeg")
    """
    return {
        "type": message_type,
        "sender": sender_name,
        "message_id": message_id,
        "data": data,
        "mime_type": mime_type,
        "timestamp": datetime.datetime.now().isoformat(),
    }


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles an incoming photo from the family group.

    Steps:
      1. Ignore messages not from the family group
      2. Get the highest resolution version of the photo
      3. Download it to temp/
      4. Encode as base64 and push to display
      5. Clean up temp file

    Args:
        update (Update):   Telegram update object containing the photo.
        context (ContextTypes.DEFAULT_TYPE): Telegram bot context.

    Returns:
        None

    Example:
        # Called automatically by python-telegram-bot when a photo arrives
    """
    if not _is_from_family_group(update):
        return

    sender_name = get_sender_name(update.message.from_user.id)
    message_id = build_message_id(update.message.from_user.id, update.message.message_id)
    logger.info(f"Photo received from {sender_name}")

    # Telegram sends multiple sizes — take the last one (highest resolution)
    best_photo = update.message.photo[-1]
    telegram_file = await context.bot.get_file(best_photo.file_id)
    local_path = await download_photo(telegram_file)

    if local_path is None:
        return

    encoded = read_as_base64(local_path)
    delete_temp_file(local_path)

    if encoded is None:
        return

    payload = _build_payload("photo", sender_name, message_id, encoded, "image/jpeg")
    await context.bot_data["display_server"].push_to_display(payload)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles an incoming video from the family group.

    Steps:
      1. Ignore messages not from the family group
      2. Download the video to temp/
      3. Encode as base64 and push to display
      4. Clean up temp file

    Args:
        update (Update):   Telegram update object containing the video.
        context (ContextTypes.DEFAULT_TYPE): Telegram bot context.

    Returns:
        None
    """
    if not _is_from_family_group(update):
        return

    sender_name = get_sender_name(update.message.from_user.id)
    message_id = build_message_id(update.message.from_user.id, update.message.message_id)
    logger.info(f"Video received from {sender_name}")

    telegram_file = await context.bot.get_file(update.message.video.file_id)
    local_path = await download_video(telegram_file)

    if local_path is None:
        return

    encoded = read_as_base64(local_path)
    delete_temp_file(local_path)

    if encoded is None:
        return

    payload = _build_payload("video", sender_name, message_id, encoded, "video/mp4")
    await context.bot_data["display_server"].push_to_display(payload)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles an incoming voice message from the family group.

    Steps:
      1. Ignore messages not from the family group
      2. Download the voice file to temp/
      3. Encode as base64 and push to display (auto-plays on iPad)
      4. Clean up temp file

    Args:
        update (Update):   Telegram update object containing the voice message.
        context (ContextTypes.DEFAULT_TYPE): Telegram bot context.

    Returns:
        None
    """
    if not _is_from_family_group(update):
        return

    sender_name = get_sender_name(update.message.from_user.id)
    message_id = build_message_id(update.message.from_user.id, update.message.message_id)
    logger.info(f"Voice message received from {sender_name}")

    telegram_file = await context.bot.get_file(update.message.voice.file_id)
    local_path = await download_voice(telegram_file)

    if local_path is None:
        return

    encoded = read_as_base64(local_path)
    delete_temp_file(local_path)

    if encoded is None:
        return

    payload = _build_payload("voice", sender_name, message_id, encoded, "audio/ogg")
    await context.bot_data["display_server"].push_to_display(payload)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles an incoming text message from the family group.

    Steps:
      1. Ignore messages not from the family group
      2. Convert text to speech audio file using TTS
      3. Push both the text and audio to display
      4. Clean up TTS audio temp file

    Args:
        update (Update):   Telegram update object containing the text.
        context (ContextTypes.DEFAULT_TYPE): Telegram bot context.

    Returns:
        None
    """
    if not _is_from_family_group(update):
        return

    # Ignore empty messages or system messages
    if not update.message.text:
        return

    sender_name = get_sender_name(update.message.from_user.id)
    message_id = build_message_id(update.message.from_user.id, update.message.message_id)
    text = update.message.text
    logger.info(f"Text message received from {sender_name}: {text[:50]}")

    # Generate a TTS audio file so Amma hears the message read aloud
    tts_audio_path = await text_to_speech_file(text)
    tts_encoded = read_as_base64(tts_audio_path) if tts_audio_path else None

    if tts_audio_path:
        delete_temp_file(tts_audio_path)

    # Push the text message — display shows text big + plays TTS audio
    payload = _build_payload("text", sender_name, message_id, text)
    if tts_encoded:
        payload["tts_audio"] = tts_encoded

    await context.bot_data["display_server"].push_to_display(payload)


async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles an incoming video note (round video) from the family group.

    Steps:
      1. Ignore messages not from the family group
      2. Download the video note to temp/
      3. Encode as base64 and push to display
      4. Clean up temp file

    Args:
        update (Update):   Telegram update object with video_note.
        context (ContextTypes.DEFAULT_TYPE): Telegram bot context.

    Returns:
        None
    """
    if not _is_from_family_group(update):
        return

    sender_name = get_sender_name(update.message.from_user.id)
    message_id = build_message_id(update.message.from_user.id, update.message.message_id)
    logger.info(f"Video note received from {sender_name}")

    telegram_file = await context.bot.get_file(update.message.video_note.file_id)
    local_path = await download_video(telegram_file)

    if local_path is None:
        return

    encoded = read_as_base64(local_path)
    delete_temp_file(local_path)

    if encoded is None:
        return

    payload = _build_payload("video", sender_name, message_id, encoded, "video/mp4")
    await context.bot_data["display_server"].push_to_display(payload)


def _is_from_family_group(update: Update) -> bool:
    """
    Checks if a Telegram update came from the family group chat.

    Steps:
      1. Check that the update has a message
      2. Check that the chat ID matches FAMILY_GROUP_CHAT_ID
      3. Return True if it matches, False otherwise

    Args:
        update (Update): Telegram update to check.

    Returns:
        bool: True if message is from the family group, False otherwise.

    Example:
        if not _is_from_family_group(update):
            return   # Ignore messages from other chats
    """
    if update.message is None:
        return False

    if update.message.chat_id != config.FAMILY_GROUP_CHAT_ID:
        logger.debug(f"Ignoring message from non-family chat: {update.message.chat_id}")
        return False

    return True


async def run_bot(display_server) -> None:
    """
    Builds, configures, and runs the Telegram bot until stopped.

    Steps:
      1. Build the Application with the bot token
      2. Store display_server in bot_data so handlers can reach it
      3. Register message handlers for all content types
      4. Initialize and start the app, then begin polling
      5. Suspend until cancelled by the TaskGroup (Ctrl+C or crash)
      6. Shut down polling and the app lifecycle cleanly

    Args:
        display_server (DisplayServer): The running display server instance,
                                        used to push content to the iPad.

    Returns:
        None — runs indefinitely until stopped.

    Example:
        # Called from main.py
        await run_bot(display_server=my_display_server)
    """
    global _bot_app

    logger.info("Building Telegram bot application...")

    # Build the application with our bot token
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Store display_server in bot_data so handlers can reach it
    # via context.bot_data["display_server"]
    # (Application uses __slots__ — direct attribute assignment is not allowed)
    app.bot_data["display_server"] = display_server

    # Register handlers — one per message type
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Store globally so send_amma_voice_to_group() can use it
    _bot_app = app

    logger.info("Telegram bot started — listening for family messages...")
    logger.info(f"Monitoring group chat ID: {config.FAMILY_GROUP_CHAT_ID}")

    # python-telegram-bot v20+ must NOT use run_polling() inside an existing
    # asyncio event loop (asyncio.run() in main.py owns the loop).
    # The correct pattern is the async context manager with explicit lifecycle.
    try:
        async with app:
            await app.initialize()
            await app.start()
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram polling active — waiting for family messages...")

            # Suspend here until the TaskGroup cancels this task (Ctrl+C or crash)
            await asyncio.get_event_loop().create_future()

    except asyncio.CancelledError:
        logger.info("Telegram bot shutting down cleanly...")
    finally:
        # Graceful shutdown — stop polling then the app lifecycle
        try:
            if app.updater.running:
                await app.updater.stop()
            if app.running:
                await app.stop()
        except Exception as shutdown_error:
            logger.warning(f"Minor error during bot shutdown: {shutdown_error}")
