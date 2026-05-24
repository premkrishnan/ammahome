# ============================================================
# FILE: main.py
#
# PURPOSE:
#   Entry point for AmmaHome. Starts all services in the
#   correct order and keeps them running. On --test flag,
#   validates configuration and exits without connecting.
#
# INPUTS:
#   - Command line: optional --test flag for config validation
#
# OUTPUTS:
#   - Starts Telegram bot, WebSocket display server,
#     HTTP file server, and heartbeat monitor
#
# DEPENDENCIES:
#   - config.py
#   - services/bot.py
#   - services/display_server.py
#   - services/heartbeat.py
#   - utils/logger.py
#   - utils/file_utils.py
#
# HOW TO RUN:
#   python main.py          ← starts AmmaHome normally
#   python main.py --test   ← validates config and exits
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import asyncio
import sys

import config
from utils.file_utils import clear_all_temp_files
from utils.logger import get_logger

logger = get_logger(__name__)


def run_config_test() -> None:
    """
    Validates the configuration and prints a summary, then exits.

    Steps:
      1. Import config (this triggers all validation and _require checks)
      2. Print the config summary
      3. Exit with code 0 (success)

    Args:
        None

    Returns:
        None (exits the process)

    Example:
        python main.py --test
        # Prints config summary and exits cleanly
    """
    config.print_config_summary()
    print("✅  Config test passed — AmmaHome is ready to start.\n")
    sys.exit(0)


async def start_all_services() -> None:
    """
    Starts all AmmaHome services concurrently.

    Steps:
      1. Clear any leftover temp files from a previous run
      2. Print the startup config summary
      3. Start the WebSocket display server
      4. Start the HTTP server (serves the iPad web page)
      5. Start the heartbeat monitor
      6. Start the Telegram bot (this runs until interrupted)

    Args:
        None

    Returns:
        None — runs until KeyboardInterrupt (Ctrl+C)
    """
    # Step 1: Clean up temp files left over from a previous run
    clear_all_temp_files()

    # Step 2: Print a readable summary of what is loaded
    config.print_config_summary()

    # Import services here (not at top) so config errors show first
    from services.display_server import DisplayServer
    from services.heartbeat import HeartbeatMonitor
    from services.bot import run_bot

    # Step 3: Create the display server (WebSocket + HTTP)
    display_server = DisplayServer()

    # Step 4: Create the heartbeat monitor
    heartbeat_monitor = HeartbeatMonitor(display_server=display_server)

    # Step 5: Start display server and heartbeat monitor as background tasks
    logger.info("Starting WebSocket display server...")
    logger.info("Starting heartbeat monitor...")

    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(display_server.start(), name="display_server")
        task_group.create_task(heartbeat_monitor.start(), name="heartbeat_monitor")
        task_group.create_task(run_bot(display_server=display_server), name="telegram_bot")


def main() -> None:
    """
    Main entry point — parses arguments and starts AmmaHome.

    Steps:
      1. Check if --test flag was passed
      2. If test, run config validation and exit
      3. Otherwise, start all services via asyncio

    Args:
        None

    Returns:
        None
    """
    # Handle --test flag for config validation without starting services
    if "--test" in sys.argv:
        run_config_test()

    logger.info("AmmaHome starting up...")

    try:
        asyncio.run(start_all_services())
    except KeyboardInterrupt:
        logger.info("AmmaHome stopped by user (Ctrl+C). Goodbye.")
    except Exception as error:
        logger.error(f"AmmaHome crashed unexpectedly: {error}")
        logger.error("Fix: Check ammahome.log for the full error details")
        sys.exit(1)


if __name__ == "__main__":
    main()
