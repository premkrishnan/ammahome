# ============================================================
# FILE: services/tts.py
#
# PURPOSE:
#   Converts a text message to a Malayalam (or English) audio
#   file so Amma can hear text messages read aloud on the iPad.
#   Uses gTTS (Google Text-to-Speech) as the primary backend,
#   with macOS 'say' as a fallback for offline situations.
#
# INPUTS:
#   - text (str): The message text to convert to speech
#
# OUTPUTS:
#   - pathlib.Path to a .mp3 audio file in temp/
#   - None if TTS fails completely
#
# DEPENDENCIES:
#   - gTTS (pip install gTTS) — requires internet
#   - config.py → TTS_LANGUAGE, TTS_BACKEND, TEMP_DIR
#   - utils/logger.py
#   - utils/file_utils.py → make_temp_path
#
# CALLED BY:
#   - services/bot.py → handle_text()
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import subprocess
from pathlib import Path

import config
from utils.file_utils import make_temp_path
from utils.logger import get_logger

logger = get_logger(__name__)


async def text_to_speech_file(text: str) -> Path | None:
    """
    Converts text to a speech audio file using the configured TTS backend.

    Steps:
      1. Check which TTS backend is configured
      2. If "google", try gTTS first (supports Malayalam)
      3. If gTTS fails or backend is "say", fall back to macOS 'say'
      4. Return the path to the generated audio file

    Args:
        text (str): The text to convert to speech.
                    Example: "Hello Amma, we miss you!"

    Returns:
        Path: Path to the generated .mp3 audio file.
              Example: Path("temp/tts_a1b2c3d4.mp3")
        None: If all TTS backends fail.

    Example:
        audio_path = await text_to_speech_file("Hello Amma!")
        if audio_path:
            encoded = read_as_base64(audio_path)
    """
    if config.TTS_BACKEND == "google":
        result = _gtts_to_file(text)
        if result is not None:
            return result
        # gTTS failed (probably no internet) — try macOS fallback
        logger.warning("gTTS failed — falling back to macOS 'say' command")

    return _macos_say_to_file(text)


def _gtts_to_file(text: str) -> Path | None:
    """
    Generates speech using gTTS (Google Text-to-Speech).

    Steps:
      1. Import gTTS (catches ImportError if not installed)
      2. Create a gTTS object with the configured language
      3. Save to a temp .mp3 file
      4. Return the path

    Args:
        text (str): Text to convert. Example: "Amma, we love you!"

    Returns:
        Path: Path to the .mp3 file. Example: Path("temp/tts_a1b2c3.mp3")
        None: If gTTS is not installed or the API call fails.

    Example:
        path = _gtts_to_file("Hello")
        # Returns temp/tts_abc123.mp3 or None
    """
    try:
        from gtts import gTTS
    except ImportError:
        logger.error("gTTS not installed. Fix: pip install gTTS")
        return None

    output_path = make_temp_path("tts", "mp3")

    try:
        tts = gTTS(text=text, lang=config.TTS_LANGUAGE, slow=False)
        tts.save(str(output_path))
        logger.info(f"gTTS audio saved to {output_path.name} (lang={config.TTS_LANGUAGE})")
        return output_path
    except Exception as error:
        logger.error(f"gTTS failed: {error}")
        logger.error("Fix: Check internet connection — gTTS requires internet access")
        return None


def _macos_say_to_file(text: str) -> Path | None:
    """
    Generates speech using the macOS built-in 'say' command.

    Steps:
      1. Create a temp .aiff path for the 'say' output
      2. Create a temp .mp3 path for the converted output
      3. Run 'say' command to generate .aiff
      4. Convert .aiff to .mp3 using afconvert
      5. Delete the intermediate .aiff file
      6. Return the .mp3 path

    Note:
        macOS 'say' does not support Malayalam.
        This is an English-only fallback for offline situations.

    Args:
        text (str): Text to convert. Example: "Hello"

    Returns:
        Path: Path to the .mp3 file. Example: Path("temp/tts_abc123.mp3")
        None: If the 'say' command or conversion fails.

    Example:
        path = _macos_say_to_file("Hello Amma")
        # Returns temp/tts_abc123.mp3 or None (English only)
    """
    aiff_path = make_temp_path("tts_raw", "aiff")
    mp3_path = make_temp_path("tts", "mp3")

    try:
        # Step 1: Generate speech as AIFF using macOS 'say'
        subprocess.run(
            ["say", "-o", str(aiff_path), text],
            check=True,
            capture_output=True,
        )

        # Step 2: Convert AIFF to MP3 using afconvert (built into macOS)
        subprocess.run(
            ["afconvert", str(aiff_path), str(mp3_path), "-f", "mp4f", "-d", "aac"],
            check=True,
            capture_output=True,
        )

        # Step 3: Remove the intermediate AIFF file
        if aiff_path.exists():
            aiff_path.unlink()

        logger.info(f"macOS 'say' audio saved to {mp3_path.name} (English only)")
        return mp3_path

    except subprocess.CalledProcessError as error:
        logger.error(f"macOS 'say' command failed: {error}")
        logger.error("Fix: This only works on macOS. Check that 'say' is available.")
        return None
    except Exception as error:
        logger.error(f"TTS fallback failed unexpectedly: {error}")
        return None
