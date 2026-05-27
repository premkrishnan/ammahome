# ============================================================
# FILE: services/display_server.py
#
# PURPOSE:
#   Runs a single combined aiohttp server for the iPad display.
#   HTTP routes serve the static display/ web app; the /ws route
#   handles WebSocket upgrades for real-time communication.
#   Listens on the PORT env var (set by Railway) or falls back to
#   config.PORT. Maintains a message queue so content is not lost
#   when the iPad is briefly offline, and flushes on reconnect.
#
# INPUTS:
#   - JSON payloads from bot.py via push_to_display()
#   - WebSocket messages from the iPad (ack, heartbeat, voice_reply)
#
# OUTPUTS:
#   - JSON payloads sent over WebSocket to all connected iPads
#   - HTTP responses serving display/ static files to the iPad
#   - Heartbeat timestamps tracked for heartbeat.py
#   - Voice reply files saved to temp/ for bot.py to forward
#
# DEPENDENCIES:
#   - aiohttp (pip install aiohttp)
#   - config.py → DISPLAY_SERVER_HOST, PORT, MAX_MEDIA_QUEUE_SIZE,
#                  TEMP_DIR, DISPLAY_DIR
#   - utils/logger.py
#   - utils/file_utils.py → make_temp_path
#
# CALLED BY:
#   - main.py → display_server.start()
#   - services/bot.py → display_server.push_to_display()
#   - services/heartbeat.py → display_server.send_chime(),
#                              display_server.is_ipad_connected()
#
# AUTHOR: AmmaHome
# LAST UPDATED: 2026-05-27
# ============================================================

import asyncio
import base64
import datetime
import json
from pathlib import Path

from aiohttp import web

import config
from utils.file_utils import make_temp_path
from utils.logger import get_logger

logger = get_logger(__name__)


class DisplayServer:
    """
    Manages the WebSocket and HTTP servers that communicate with the iPad.

    The WebSocket server pushes content to the iPad and receives
    ack/heartbeat/voice_reply messages back. The HTTP server serves
    the static display web page from the display/ directory.
    """

    def __init__(self) -> None:
        """
        Initialises the DisplayServer with an empty client set and queue.

        Steps:
          1. Create an empty set for connected aiohttp WebSocketResponse clients
          2. Create an empty list for the offline message queue
          3. Initialise the last heartbeat timestamp to None
          4. Create a voice reply callback slot (set by external code)

        Args:
            None

        Returns:
            None

        Example:
            server = DisplayServer()
            await server.start()
        """
        # Active WebSocket connections (one per iPad browser tab)
        self._clients: set[web.WebSocketResponse] = set()

        # Queue for messages received while iPad was offline
        # Flushed automatically when iPad reconnects
        self._queue: list[dict] = []

        # Timestamp of the last heartbeat received from the iPad
        # Used by HeartbeatMonitor to detect disconnection
        self.last_heartbeat_at: datetime.datetime | None = None

        # Optional callback invoked when Amma sends a voice reply
        # Set by bot.py or main.py: server.on_voice_reply = my_handler
        self.on_voice_reply = None

    # ── Public interface ─────────────────────────────────────

    def is_ipad_connected(self) -> bool:
        """
        Returns True if at least one iPad is connected via WebSocket.

        Steps:
          1. Check if the connected clients set is non-empty

        Args:
            None

        Returns:
            bool: True if one or more iPads are connected.
                  False if no iPads are connected.

        Example:
            if server.is_ipad_connected():
                logger.info("iPad is online")
        """
        return len(self._clients) > 0

    async def push_to_display(self, payload: dict) -> None:
        """
        Sends a content payload to all connected iPads.

        Steps:
          1. If no iPads connected, add payload to the offline queue
          2. If queue is full, drop the oldest message to make room
          3. If iPads are connected, send payload as JSON to all of them
          4. If send fails for a client, remove it from the set

        Args:
            payload (dict): A complete WebSocket payload dict.
                            Example: {"type": "photo", "sender": "Prem",
                                      "data": "...", "mime_type": "image/jpeg",
                                      "message_id": "123_42",
                                      "timestamp": "2026-05-24T14:32:01"}

        Returns:
            None

        Example:
            await server.push_to_display({"type": "text", "sender": "Prem",
                                          "data": "Hello Amma!", ...})
        """
        if not self._clients:
            # No iPad connected — queue the message for later
            if len(self._queue) >= config.MAX_MEDIA_QUEUE_SIZE:
                dropped = self._queue.pop(0)
                logger.warning(
                    f"Queue full — dropped oldest message "
                    f"(type={dropped.get('type')}, sender={dropped.get('sender')})"
                )
            self._queue.append(payload)
            logger.info(
                f"iPad offline — queued {payload.get('type')} from {payload.get('sender')} "
                f"({len(self._queue)}/{config.MAX_MEDIA_QUEUE_SIZE} queued)"
            )
            return

        await self._broadcast(payload)

    async def send_chime(self) -> None:
        """
        Sends a chime notification to the iPad.

        Steps:
          1. Build a minimal chime payload with the current timestamp
          2. Broadcast it to all connected iPads

        Args:
            None

        Returns:
            None

        Example:
            await server.send_chime()
            # iPad plays the chime sound
        """
        payload = {
            "type": "chime",
            "sender": "AmmaHome",
            "data": None,
            "mime_type": None,
            "message_id": None,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        await self._broadcast(payload)
        logger.info("Chime sent to iPad")

    # ── Server startup ────────────────────────────────────────

    async def start(self) -> None:
        """
        Starts the combined HTTP + WebSocket server on a single port.

        Steps:
          1. Build the aiohttp app (HTTP routes + /ws WebSocket route)
          2. Start the server on DISPLAY_SERVER_HOST:PORT
          3. Log the iPad display URL and WebSocket path
          4. Run until the task is cancelled

        Args:
            None

        Returns:
            None — runs indefinitely until cancelled.

        Example:
            await server.start()
        """
        app = self._build_http_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(
            runner,
            config.DISPLAY_SERVER_HOST,
            config.PORT,
        )
        await site.start()

        logger.info(
            f"Combined HTTP+WebSocket server listening on "
            f"http://{config.DISPLAY_SERVER_HOST}:{config.PORT}"
        )
        logger.info(
            f"WebSocket path: ws://{config.DISPLAY_SERVER_HOST}:{config.PORT}/ws"
        )
        logger.info(
            f"iPad display URL: http://{config.DISPLAY_SERVER_HOST}:{config.PORT}"
        )

        # Run forever until the task is cancelled
        await asyncio.get_event_loop().create_future()

    # ── WebSocket connection handler ──────────────────────────

    async def _handle_client(
        self, request: web.Request
    ) -> web.WebSocketResponse:
        """
        Handles a single WebSocket connection from an iPad via aiohttp.

        Steps:
          1. Perform the WebSocket handshake
          2. Register the new client
          3. Flush the offline queue to the newly connected iPad
          4. Loop receiving messages until the connection closes
          5. Dispatch each incoming message to the right handler
          6. Deregister the client when the connection drops

        Args:
            request (web.Request): The aiohttp HTTP upgrade request.

        Returns:
            web.WebSocketResponse: The completed WebSocket response object.

        Example:
            # Registered as aiohttp route: app.router.add_get('/ws', ...)
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        client_addr = request.remote
        logger.info(f"iPad connected from {client_addr}")
        self._clients.add(ws)

        # Flush any queued messages to the newly connected iPad
        await self._flush_queue(ws)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._dispatch_incoming(msg.data)
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(
                        f"WebSocket error from {client_addr}: {ws.exception()}"
                    )
        except Exception as error:
            logger.error(f"Unexpected error on WebSocket connection: {error}")
        finally:
            self._clients.discard(ws)
            logger.info(f"iPad removed from client set: {client_addr}")

        return ws

    async def _dispatch_incoming(self, raw_message: str) -> None:
        """
        Parses and dispatches an incoming message from the iPad.

        Steps:
          1. Parse the raw string as JSON
          2. Check the "type" field
          3. Route to handle_ack, handle_heartbeat, or handle_voice_reply

        Args:
            raw_message (str): Raw JSON string from the iPad WebSocket.
                               Example: '{"type": "heartbeat", "timestamp": "..."}'

        Returns:
            None

        Example:
            await self._dispatch_incoming('{"type": "ack", "message_id": "123_42"}')
        """
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError as error:
            logger.error(f"Received invalid JSON from iPad: {error}")
            return

        msg_type = message.get("type")

        if msg_type == "heartbeat":
            self._handle_heartbeat(message)
        elif msg_type == "ack":
            self._handle_ack(message)
        elif msg_type == "voice_reply":
            await self._handle_voice_reply(message)
        else:
            logger.warning(f"Unknown message type from iPad: {msg_type!r}")

    def _handle_heartbeat(self, message: dict) -> None:
        """
        Records the timestamp of the latest heartbeat from the iPad.

        Steps:
          1. Update last_heartbeat_at to now
          2. Log at debug level (heartbeats are frequent)

        Args:
            message (dict): Parsed heartbeat message from the iPad.
                            Example: {"type": "heartbeat", "timestamp": "..."}

        Returns:
            None

        Example:
            self._handle_heartbeat({"type": "heartbeat", "timestamp": "..."})
        """
        self.last_heartbeat_at = datetime.datetime.now()
        logger.debug("Heartbeat received from iPad")

    def _handle_ack(self, message: dict) -> None:
        """
        Logs that Amma acknowledged a message on the iPad.

        Steps:
          1. Extract message_id from the payload
          2. Log the acknowledgement

        Args:
            message (dict): Parsed ack message from the iPad.
                            Example: {"type": "ack", "message_id": "123_42"}

        Returns:
            None

        Example:
            self._handle_ack({"type": "ack", "message_id": "123_42"})
        """
        message_id = message.get("message_id", "unknown")
        logger.info(f"Amma acknowledged message: {message_id}")

    async def _handle_voice_reply(self, message: dict) -> None:
        """
        Saves Amma's recorded voice reply and triggers forwarding to family.

        Steps:
          1. Decode the base64 audio from the message
          2. Save it to a temp .ogg file
          3. Call self.on_voice_reply callback if set

        Args:
            message (dict): Parsed voice_reply message from the iPad.
                            Example: {"type": "voice_reply", "data": "<base64>"}

        Returns:
            None

        Example:
            await self._handle_voice_reply({"type": "voice_reply", "data": "..."})
        """
        audio_b64 = message.get("data")
        if not audio_b64:
            logger.error("Received voice_reply with no audio data — ignoring")
            return

        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception as error:
            logger.error(f"Failed to decode Amma's voice reply audio: {error}")
            return

        voice_path = make_temp_path("amma_voice", "ogg")
        try:
            voice_path.write_bytes(audio_bytes)
            logger.info(f"Amma's voice reply saved to {voice_path.name}")
        except OSError as error:
            logger.error(f"Failed to save Amma's voice reply: {error}")
            return

        # Forward to family via the registered callback (set in main.py)
        if self.on_voice_reply is not None:
            try:
                await self.on_voice_reply(voice_path)
            except Exception as error:
                logger.error(f"Voice reply callback failed: {error}")
        else:
            logger.warning("Voice reply received but no on_voice_reply callback is set")

    # ── Queue management ──────────────────────────────────────

    async def _flush_queue(self, ws: web.WebSocketResponse) -> None:
        """
        Sends all queued messages to a newly connected iPad.

        Steps:
          1. Check if the queue has messages
          2. Send each message in order using aiohttp send_str
          3. Clear the queue after successful flush

        Args:
            ws (web.WebSocketResponse): The newly connected iPad socket.

        Returns:
            None

        Example:
            await self._flush_queue(ws)
            # All queued messages are delivered to the iPad
        """
        if not self._queue:
            return

        logger.info(f"Flushing {len(self._queue)} queued message(s) to iPad...")

        for payload in self._queue:
            try:
                await ws.send_str(json.dumps(payload))
                logger.info(
                    f"Flushed queued {payload.get('type')} "
                    f"from {payload.get('sender')} to iPad"
                )
            except Exception as error:
                logger.error(f"Failed to flush queued message to iPad: {error}")
                # Stop flushing — iPad may have disconnected again
                return

        self._queue.clear()
        logger.info("Queue flushed — all queued messages delivered")

    # ── Broadcast helpers ─────────────────────────────────────

    async def _broadcast(self, payload: dict) -> None:
        """
        Sends a payload to every connected iPad.

        Steps:
          1. Serialise the payload to JSON
          2. Send to each connected client
          3. Remove any client that fails (connection dropped)

        Args:
            payload (dict): The payload to send to all connected iPads.

        Returns:
            None

        Example:
            await self._broadcast({"type": "chime", ...})
        """
        if not self._clients:
            logger.debug("Broadcast called with no connected clients")
            return

        json_payload = json.dumps(payload)
        disconnected: set[web.WebSocketResponse] = set()

        for client in self._clients:
            try:
                await client.send_str(json_payload)
                logger.info(
                    f"Sent {payload.get('type')} from {payload.get('sender')} to iPad"
                )
            except Exception as error:
                logger.error(f"Failed to send to an iPad client: {error}")
                disconnected.add(client)

        # Clean up any clients that failed
        self._clients -= disconnected

    # ── HTTP server ───────────────────────────────────────────

    def _build_http_app(self) -> web.Application:
        """
        Builds the aiohttp application that serves HTTP and WebSocket on one port.

        Steps:
          1. Create an aiohttp Application
          2. Add the /ws route for WebSocket upgrades
          3. Add the root route serving index.html
          4. Add the static file route for CSS/JS assets
          5. Return the application

        Args:
            None

        Returns:
            web.Application: Configured aiohttp app ready to be run.

        Example:
            app = self._build_http_app()
            runner = web.AppRunner(app)
        """
        app = web.Application()
        app.router.add_get("/ws", self._handle_client)
        app.router.add_get("/", self._serve_index)
        app.router.add_static("/", config.DISPLAY_DIR, show_index=False)
        return app

    async def _serve_index(self, request: web.Request) -> web.Response:
        """
        Serves the display/index.html file for the root URL.

        Steps:
          1. Build the path to display/index.html
          2. Read and return the HTML content

        Args:
            request (web.Request): The incoming HTTP request.

        Returns:
            web.Response: The index.html content with text/html content type.

        Example:
            # GET http://192.168.1.10:8080/ → returns index.html
        """
        index_path = config.DISPLAY_DIR / "index.html"
        if not index_path.exists():
            logger.error(f"display/index.html not found at {index_path}")
            return web.Response(
                text="AmmaHome display not found. Check display/ directory.",
                status=404,
            )
        return web.FileResponse(index_path)
