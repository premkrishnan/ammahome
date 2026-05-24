# ============================================================
# FILE: utils/logger.py
#
# PURPOSE:
#   Sets up a single shared logger for the entire AmmaHome
#   project. Every service imports get_logger() from here
#   so all log output has consistent formatting and goes to
#   both the terminal and a log file.
#
# INPUTS:
#   - module_name (str): passed as __name__ from each file
#
# OUTPUTS:
#   - A configured logging.Logger instance
#
# DEPENDENCIES:
#   - Python standard library: logging, pathlib
#
# CALLED BY:
#   - Every service and utility file in the project
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import logging
import sys
from pathlib import Path

# Log file lives in the project root — easy to find when debugging
LOG_FILE_PATH = Path(__file__).parent.parent / "ammahome.log"

# Track whether the root logger has been configured already.
# We only want to add handlers once, not once per module import.
_logging_configured = False


def _configure_root_logger() -> None:
    """
    Configures the root logger with console and file handlers.

    Steps:
      1. Create a formatter with timestamp, level, module, message
      2. Add a StreamHandler so logs appear in the terminal
      3. Add a FileHandler so logs are saved to ammahome.log
      4. Set root logger level to INFO

    Args:
        None

    Returns:
        None
    """
    global _logging_configured

    if _logging_configured:
        return

    # Format: [HH:MM:SS] LEVEL    module_name  — message
    log_format = "[%(asctime)s] %(levelname)-8s %(name)-30s — %(message)s"
    date_format = "%H:%M:%S"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # Console handler — shows logs in the terminal while running
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # File handler — saves all logs to ammahome.log for debugging
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Apply both handlers to the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _logging_configured = True


def get_logger(module_name: str) -> logging.Logger:
    """
    Returns a configured logger for the given module name.

    Steps:
      1. Configure the root logger if not already done
      2. Return a named child logger for this module

    Args:
        module_name (str): Typically passed as __name__ from the caller.
                           Example: "services.bot", "services.heartbeat"

    Returns:
        logging.Logger: A ready-to-use logger instance.

    Example:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Bot started successfully")
        logger.error("Telegram connection failed: timeout")
    """
    _configure_root_logger()
    return logging.getLogger(module_name)
