# ============================================================
# FILE: config.py
#
# PURPOSE:
#   Central configuration for AmmaHome. Loads all settings
#   from the .env file and exposes them as typed constants.
#   Every magic value in the project lives here — never
#   hardcoded inside service files.
#
# INPUTS:
#   - .env file in the project root
#
# OUTPUTS:
#   - Typed constants imported by all service files
#
# DEPENDENCIES:
#   - python-dotenv (pip install python-dotenv)
#
# CALLED BY:
#   - All service files and main.py
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from the project root directory
load_dotenv()


# ── Helper: fail loudly if a required variable is missing ────
def _require(variable_name: str) -> str:
    """
    Reads a required environment variable and exits clearly if missing.

    Steps:
      1. Look up the variable name in os.environ
      2. If found, return the value
      3. If missing, print a clear error message and exit

    Args:
        variable_name (str): The name of the required env variable.
                             Example: "TELEGRAM_BOT_TOKEN"

    Returns:
        str: The value of the environment variable.

    Raises:
        SystemExit: If the variable is not set in .env
    """
    value = os.getenv(variable_name)
    if not value:
        print(f"\n❌  AmmaHome config error: '{variable_name}' is missing.")
        print(f"    Fix: Open your .env file and set {variable_name}=your_value")
        print(f"    See .env.example for a complete template.\n")
        sys.exit(1)
    return value


# ── Telegram ─────────────────────────────────────────────────

# Bot token from @BotFather — required to connect to Telegram API
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

# Chat ID of the family Telegram group — negative number for groups
FAMILY_GROUP_CHAT_ID: int = int(_require("FAMILY_GROUP_CHAT_ID"))


# ── Display Server ────────────────────────────────────────────

# Mac's local IP address — iPad connects to this on home Wi-Fi
DISPLAY_SERVER_HOST: str = os.getenv("DISPLAY_SERVER_HOST", "0.0.0.0")

# WebSocket port — bot pushes content to iPad over this connection
DISPLAY_SERVER_PORT: int = int(os.getenv("DISPLAY_SERVER_PORT", "8765"))

# HTTP port — iPad Safari loads the display web page from this port
DISPLAY_WEB_PORT: int = int(os.getenv("DISPLAY_WEB_PORT", "8080"))


# ── Reminder & Heartbeat ──────────────────────────────────────

# How often to chime if Amma has not acknowledged a message
# Default: 900 seconds = 15 minutes
REMINDER_INTERVAL_SECONDS: int = int(os.getenv("REMINDER_INTERVAL_SECONDS", "900"))

# How often the iPad sends a heartbeat ping to confirm it is alive
# Default: 300 seconds = 5 minutes
HEARTBEAT_INTERVAL_SECONDS: int = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "300"))

# Alert the family if no heartbeat is received within this many minutes
# Default: 15 minutes
HEARTBEAT_TIMEOUT_MINUTES: int = int(os.getenv("HEARTBEAT_TIMEOUT_MINUTES", "15"))


# ── TTS (Text-to-Speech) ──────────────────────────────────────

# Language code for reading text messages aloud
# "ml" = Malayalam, "en" = English
TTS_LANGUAGE: str = os.getenv("TTS_LANGUAGE", "ml")

# Which TTS engine to use
# "google" = gTTS (internet required, supports Malayalam)
# "say"    = macOS built-in (offline, English only)
TTS_BACKEND: str = os.getenv("TTS_BACKEND", "google")


# ── Media Queue ───────────────────────────────────────────────

# Maximum number of messages to hold in memory if iPad is offline.
# Prevents Amma from missing messages during a short disconnect.
MAX_MEDIA_QUEUE_SIZE: int = int(os.getenv("MAX_MEDIA_QUEUE_SIZE", "10"))


# ── Family Members ────────────────────────────────────────────

# Maps Telegram user_id (as string) to a friendly display name.
# Shown on Amma's screen so she knows who sent the message.
# Example: {"123456789": "Prem", "987654321": "Priya"}
_family_names_raw: str = os.getenv("FAMILY_MEMBER_NAMES", "{}")
try:
    FAMILY_MEMBER_NAMES: dict[str, str] = json.loads(_family_names_raw)
except json.JSONDecodeError:
    print("\n❌  AmmaHome config error: FAMILY_MEMBER_NAMES is not valid JSON.")
    print('    Fix: Check the format in .env — example: {"123456789": "Prem"}')
    print("    Make sure to use double quotes inside the JSON.\n")
    sys.exit(1)


# ── File Paths ────────────────────────────────────────────────

# Root directory of the project (where this config.py lives)
PROJECT_ROOT: Path = Path(__file__).parent

# Temporary directory for downloaded media files
# Files here are deleted after being sent to the display
TEMP_DIR: Path = PROJECT_ROOT / "temp"

# Display web app directory — served to the iPad browser
DISPLAY_DIR: Path = PROJECT_ROOT / "display"

# Ensure temp directory exists at startup
TEMP_DIR.mkdir(exist_ok=True)


# ── Startup Summary ───────────────────────────────────────────

def print_config_summary() -> None:
    """
    Prints a human-readable summary of the loaded configuration.

    Steps:
      1. Print each major config section with its values
      2. Mask the bot token for security
      3. Show the iPad connection URL

    Args:
        None

    Returns:
        None
    """
    masked_token = TELEGRAM_BOT_TOKEN[:8] + "..." + TELEGRAM_BOT_TOKEN[-4:]

    print("\n" + "=" * 60)
    print("  AmmaHome — കുടുംബം എപ്പോഴും അടുത്ത്")
    print("  (Family Always Nearby)")
    print("=" * 60)
    print(f"  Telegram bot token : {masked_token}")
    print(f"  Family group ID    : {FAMILY_GROUP_CHAT_ID}")
    print(f"  Display WebSocket  : ws://{DISPLAY_SERVER_HOST}:{DISPLAY_SERVER_PORT}")
    print(f"  iPad display URL   : http://{DISPLAY_SERVER_HOST}:{DISPLAY_WEB_PORT}")
    print(f"  Reminder interval  : every {REMINDER_INTERVAL_SECONDS // 60} minutes")
    print(f"  Heartbeat timeout  : {HEARTBEAT_TIMEOUT_MINUTES} minutes")
    print(f"  TTS language       : {TTS_LANGUAGE} ({TTS_BACKEND})")
    print(f"  Family members     : {list(FAMILY_MEMBER_NAMES.values())}")
    print("=" * 60 + "\n")
