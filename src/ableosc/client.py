"""OSC client for communicating with AbletonOSC.

AbletonOSC is a Python Remote Script that runs inside Ableton Live and exposes
its API over OSC/UDP. This client handles:
- Sending OSC messages to AbletonOSC (port 11000 by default)
- Receiving responses from AbletonOSC (port 11001 by default)
- Request/response correlation by OSC address
- Real-time listener subscriptions

AbletonOSC protocol conventions:
- GET:    send /live/*/get/<prop> [args...], receive response on same address
- SET:    send /live/*/set/<prop> [args...], fire-and-forget (no response)
- ACTION: send /live/*/<action> [args...], fire-and-forget
- LISTEN: send /live/*/start_listen/<prop> [args...], receive events on get address
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from typing import Any, Callable

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


class OscClient:
    """Async OSC client for AbletonOSC.

    Usage::

        client = OscClient()
        await client.start()

        # Request/response GET
        result = await client.get("/live/song/get/tempo")
        tempo = result[0]  # (120.0,)

        # Fire-and-forget SET/action
        client.send("/live/song/set/tempo", 128.0)
        client.send("/live/song/start_playing")

        # Real-time listener
        def on_tempo_change(address, *args):
            print(f"Tempo changed: {args[0]}")

        client.send("/live/song/start_listen/tempo")
        client.add_listener("/live/song/get/tempo", on_tempo_change)

        await client.stop()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        send_port: int = 11000,
        receive_port: int = 11001,
    ) -> None:
        self._host = host
        self._send_port = send_port
        self._receive_port = receive_port

        self._udp_client: SimpleUDPClient | None = None
        self._transport: asyncio.BaseTransport | None = None

        # Pending GET futures: address -> FIFO queue of futures
        self._pending: dict[str, deque[asyncio.Future[tuple[Any, ...]]]] = defaultdict(
            deque
        )
        # Real-time listeners: address -> list of callbacks
        self._listeners: dict[str, list[Callable[..., None]]] = defaultdict(list)

        self._dispatcher = Dispatcher()
        self._dispatcher.set_default_handler(self._on_message)
        self._dispatcher.map("/live/error", self._on_error)

    async def start(self) -> None:
        """Start the UDP client and OSC receive server."""
        self._udp_client = SimpleUDPClient(self._host, self._send_port)
        loop = asyncio.get_running_loop()
        server = AsyncIOOSCUDPServer(
            ("0.0.0.0", self._receive_port),
            self._dispatcher,
            loop,
        )
        self._transport, _ = await server.create_serve_endpoint()
        logger.info(
            "OscClient started — sending to %s:%d, listening on :%d",
            self._host,
            self._send_port,
            self._receive_port,
        )

    async def stop(self) -> None:
        """Shut down the receive server."""
        if self._transport:
            self._transport.close()
            self._transport = None
        logger.info("OscClient stopped")

    @property
    def is_running(self) -> bool:
        return self._transport is not None

    # ------------------------------------------------------------------
    # Internal message handling
    # ------------------------------------------------------------------

    def _on_message(self, address: str, *args: Any) -> None:
        """Dispatch an incoming OSC message to pending futures and listeners."""
        # Resolve the oldest pending future for this address (FIFO)
        pending_queue = self._pending.get(address)
        if pending_queue:
            future = pending_queue[0]
            pending_queue.popleft()
            if not future.done():
                future.set_result(args)

        # Notify real-time listeners
        for callback in list(self._listeners.get(address, [])):
            try:
                callback(address, *args)
            except Exception:
                logger.exception("Listener error on %s", address)

    def _on_error(self, address: str, *args: Any) -> None:
        """Log errors reported by AbletonOSC."""
        logger.error("AbletonOSC error: %s", args)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        address: str,
        *args: Any,
        timeout: float = 5.0,
    ) -> tuple[Any, ...]:
        """Send an OSC request and await the response on the same address.

        Args:
            address: OSC address, e.g. "/live/song/get/tempo"
            *args:   Optional arguments to include in the request.
            timeout: Seconds to wait before raising TimeoutError.

        Returns:
            Tuple of response arguments from AbletonOSC.

        Raises:
            RuntimeError: If the client has not been started.
            TimeoutError: If no response arrives within *timeout* seconds.
        """
        if self._udp_client is None:
            raise RuntimeError("OscClient is not running — call start() first")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[Any, ...]] = loop.create_future()
        self._pending[address].append(future)

        try:
            self._udp_client.send_message(address, list(args) if args else [])
            async with asyncio.timeout(timeout):
                return await future
        except TimeoutError:
            raise TimeoutError(
                f"No response from AbletonOSC for '{address}' within {timeout}s. "
                "Is AbletonOSC installed and Ableton Live running?"
            )
        finally:
            # Always clean up the future from the queue
            try:
                self._pending[address].remove(future)
            except ValueError:
                pass

    def send(self, address: str, *args: Any) -> None:
        """Fire-and-forget OSC message (SET, action, start_listen, etc.).

        Args:
            address: OSC address, e.g. "/live/song/set/tempo"
            *args:   Arguments to include.

        Raises:
            RuntimeError: If the client has not been started.
        """
        if self._udp_client is None:
            raise RuntimeError("OscClient is not running — call start() first")
        self._udp_client.send_message(address, list(args) if args else [])

    def add_listener(self, address: str, callback: Callable[..., None]) -> None:
        """Register a callback for real-time updates from AbletonOSC.

        AbletonOSC sends updates on the GET address (e.g. /live/song/get/tempo)
        whenever the value changes after calling start_listen.

        Args:
            address:  OSC address to listen on (the GET address, not start_listen).
            callback: Called as callback(address, *args) on each update.
        """
        self._listeners[address].append(callback)

    def remove_listener(self, address: str, callback: Callable[..., None]) -> None:
        """Unregister a previously added listener callback."""
        try:
            self._listeners[address].remove(callback)
        except ValueError:
            pass

    async def ping(self) -> bool:
        """Test the connection to AbletonOSC.

        Returns:
            True if AbletonOSC responds within 3 seconds.
        """
        try:
            result = await self.get("/live/test", timeout=3.0)
            return len(result) > 0
        except TimeoutError:
            return False
