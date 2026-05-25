# ============================================================
# FILE: services/heartbeat.py
#
# PURPOSE:
#   Monitors the iPad's heartbeat to detect if the display has
#   gone offline or been disconnected. If no heartbeat is received
#   within HEARTBEAT_TIMEOUT_MINUTES, sends an alert to the family
#   Telegram group. Also sends reminder chimes to the iPad if a
#   message has not been acknowledged within REMINDER_INTERVAL_SECONDS.
#
# INPUTS:
#   - Heartbeat timestamps from display_server.last_heartbeat_at
#   - is_ipad_connected() from display_server
#
# OUTPUTS:
#   - Alert messages sent to the family Telegram group
#   - Chime payloads sent to the iPad via display_server.send_chime()
#
# DEPENDENCIES:
#   - config.py → HEARTBEAT_TIMEOUT_MINUTES, HEARTBEAT_INTERVAL_SECONDS,
#                  REMINDER_INTERVAL_SECONDS, FAMILY_GROUP_CHAT_ID
#   - services/display_server.py → DisplayServer
#   - services/bot.py → get_bot_app()
#   - utils/logger.py
#
# CALLED BY:
#   - main.py → heartbeat_monitor.start()
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-24
# ============================================================

import asyncio
import datetime

import config
from utils.logger import get_logger

logger = get_logger(__name__)

# How often the heartbeat monitor loop runs (in seconds)
_CHECK_INTERVAL_SECONDS: int = 60


class HeartbeatMonitor:
    """
    Periodically checks the iPad's connection health and sends alerts.

    Runs as a background asyncio task. Never crashes — all exceptions
    are caught and logged so the monitor keeps running.
    """

    def __init__(self, display_server) -> None:
        """
        Initialises the HeartbeatMonitor with a reference to the display server.

        Steps:
          1. Store the display_server reference
          2. Initialise alert state to avoid sending duplicate alerts
          3. Track when the last reminder chime was sent

        Args:
            display_server (DisplayServer): The running display server instance.
                                            Used to check connection status and
                                            to send chimes.

        Returns:
            None

        Example:
            monitor = HeartbeatMonitor(display_server=my_server)
            await monitor.start()
        """
        self._display_server = display_server

        # True while we are waiting for the iPad to come back online.
        # Prevents sending the same "iPad offline" alert every minute.
        self._offline_alert_sent: bool = False

        # Timestamp of the last reminder chime sent to the iPad
        self._last_chime_at: datetime.datetime | None = None

    async def start(self) -> None:
        """
        Runs the heartbeat monitoring loop indefinitely.

        Steps:
          1. Wait one full check interval before the first check
             (gives the iPad time to connect at startup)
          2. Every _CHECK_INTERVAL_SECONDS seconds:
             a. Check if the iPad has timed out
             b. Check if a reminder chime should be sent
          3. On any unexpected error, log and continue (never crash)

        Args:
            None

        Returns:
            None — runs indefinitely until cancelled.

        Example:
            await monitor.start()
        """
        logger.info(
            f"Heartbeat monitor started — "
            f"checking every {_CHECK_INTERVAL_SECONDS}s, "
            f"timeout after {config.HEARTBEAT_TIMEOUT_MINUTES} minutes"
        )

        # Wait before first check — iPad needs time to connect
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

        while True:
            try:
                await self._check_heartbeat()
                await self._check_reminder()
            except Exception as error:
                logger.error(f"Heartbeat monitor loop error: {error}")
                logger.error("Fix: Check display_server and bot are running correctly")

            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

    # ── Heartbeat check ───────────────────────────────────────

    async def _check_heartbeat(self) -> None:
        """
        Checks if the iPad has missed its heartbeat deadline.

        Steps:
          1. If iPad has never sent a heartbeat and is not connected, skip
          2. Check if time since last heartbeat exceeds HEARTBEAT_TIMEOUT_MINUTES
          3. If timed out and alert not yet sent, alert the family group
          4. If heartbeat is fresh, reset the alert flag

        Args:
            None

        Returns:
            None

        Example:
            await self._check_heartbeat()
        """
        last_beat = self._display_server.last_heartbeat_at

        # If we have never received a heartbeat, don't alert yet —
        # the iPad may still be connecting for the first time.
        if last_beat is None:
            if not self._display_server.is_ipad_connected():
                logger.debug("No heartbeat yet — waiting for iPad to connect")
            return

        elapsed_minutes = (
            datetime.datetime.now() - last_beat
        ).total_seconds() / 60

        if elapsed_minutes > config.HEARTBEAT_TIMEOUT_MINUTES:
            if not self._offline_alert_sent:
                logger.warning(
                    f"iPad has not sent a heartbeat for "
                    f"{elapsed_minutes:.0f} minutes — alerting family"
                )
                await self._alert_family_ipad_offline(elapsed_minutes)
                self._offline_alert_sent = True
        else:
            # Heartbeat is fresh — reset alert flag if we had sent one
            if self._offline_alert_sent:
                logger.info("iPad heartbeat restored — clearing offline alert")
                await self._alert_family_ipad_restored()
                self._offline_alert_sent = False

    async def _alert_family_ipad_offline(self, elapsed_minutes: float) -> None:
        """
        Sends a Telegram message to the family group warning that the iPad is offline.

        Steps:
          1. Import get_bot_app from bot.py
          2. If bot is running, send the alert message
          3. Log success or failure

        Args:
            elapsed_minutes (float): How many minutes since the last heartbeat.
                                     Example: 18.3

        Returns:
            None

        Example:
            await self._alert_family_ipad_offline(18.3)
            # Family receives: "⚠️ AmmaHome: iPad has been offline for 18 minutes..."
        """
        from services.bot import get_bot_app

        bot_app = get_bot_app()
        if bot_app is None:
            logger.warning("Cannot send iPad offline alert — bot not running yet")
            return

        alert_text = (
            f"⚠️ AmmaHome: Amma's display iPad has been offline "
            f"for {elapsed_minutes:.0f} minutes.\n"
            f"Please check that the iPad is on and connected to Wi-Fi."
        )

        try:
            await bot_app.bot.send_message(
                chat_id=config.FAMILY_GROUP_CHAT_ID,
                text=alert_text,
            )
            logger.info("iPad offline alert sent to family group")
        except Exception as error:
            logger.error(f"Failed to send iPad offline alert: {error}")
            logger.error("Fix: Check FAMILY_GROUP_CHAT_ID and bot group membership")

    async def _alert_family_ipad_restored(self) -> None:
        """
        Sends a Telegram message to the family group confirming the iPad is back online.

        Steps:
          1. Import get_bot_app from bot.py
          2. If bot is running, send the restored message

        Args:
            None

        Returns:
            None

        Example:
            await self._alert_family_ipad_restored()
            # Family receives: "✅ AmmaHome: Amma's iPad is back online!"
        """
        from services.bot import get_bot_app

        bot_app = get_bot_app()
        if bot_app is None:
            return

        try:
            await bot_app.bot.send_message(
                chat_id=config.FAMILY_GROUP_CHAT_ID,
                text="✅ AmmaHome: Amma's display iPad is back online!",
            )
            logger.info("iPad restored alert sent to family group")
        except Exception as error:
            logger.error(f"Failed to send iPad restored alert: {error}")

    # ── Reminder chime ────────────────────────────────────────

    async def _check_reminder(self) -> None:
        """
        Sends a reminder chime if the iPad is connected and the reminder interval has passed.

        Steps:
          1. Check if the iPad is connected (no point chiming if offline)
          2. Check if REMINDER_INTERVAL_SECONDS has elapsed since last chime
          3. Send a chime via the display server

        Args:
            None

        Returns:
            None

        Example:
            await self._check_reminder()
        """
        if not self._display_server.is_ipad_connected():
            return

        now = datetime.datetime.now()

        if self._last_chime_at is None:
            # Set initial reference so we don't chime immediately on startup
            self._last_chime_at = now
            return

        elapsed_seconds = (now - self._last_chime_at).total_seconds()

        if elapsed_seconds >= config.REMINDER_INTERVAL_SECONDS:
            await self._display_server.send_chime()
            self._last_chime_at = now
            logger.info(
                f"Reminder chime sent "
                f"({elapsed_seconds / 60:.0f} minutes since last chime)"
            )
