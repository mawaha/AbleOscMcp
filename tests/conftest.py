"""Shared test fixtures and helpers.

Two levels of test support:

1. MockOscClient (unit tests)
   A pure-Python in-memory mock. No UDP sockets. Fast and deterministic.
   Used in all tests under tests/unit/.

2. MockAbletonOscServer (OscClient integration tests)
   A real UDP server that speaks the AbletonOSC protocol on test ports.
   Used to test the actual OscClient networking code.

3. Real Ableton + AbletonOSC (integration tests)
   tests/integration/ — marked with @pytest.mark.integration.
   Only run when ABLEOSC_INTEGRATION=1 is set in the environment.
"""

from __future__ import annotations

import asyncio
import socket
from collections import defaultdict
from typing import Any

import pytest
from pythonosc import osc_bundle_builder, osc_message_builder
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from ableosc.client import OscClient

# ---------------------------------------------------------------------------
# MockOscClient — in-memory mock for unit tests
# ---------------------------------------------------------------------------

TEST_SEND_PORT = 12000
TEST_RECEIVE_PORT = 12001


class MockOscClient:
    """Lightweight in-memory stand-in for OscClient.

    Use when_get() to pre-load responses. Call send() is recorded in
    self.sends for assertion purposes.

    Example::

        client = MockOscClient()
        client.when_get("/live/song/get/tempo", 120.0)
        result = await client.get("/live/song/get/tempo")
        assert result == (120.0,)
    """

    def __init__(self) -> None:
        # address -> tuple of return args
        self._responses: dict[str, tuple[Any, ...]] = {}
        # All get() calls: list of (address, args)
        self.gets: list[tuple[str, tuple[Any, ...]]] = []
        # All send() calls: list of (address, args)
        self.sends: list[tuple[str, tuple[Any, ...]]] = []
        # Real-time listeners: address -> list of callbacks
        self._listeners: dict[str, list] = defaultdict(list)

    def when_get(self, address: str, *response_args: Any) -> None:
        """Register a canned response for a GET request address."""
        self._responses[address] = response_args

    def clear_responses(self) -> None:
        """Remove all pre-loaded responses."""
        self._responses.clear()

    def reset_history(self) -> None:
        """Clear recorded calls."""
        self.gets.clear()
        self.sends.clear()

    # -- OscClient interface --

    async def get(
        self, address: str, *args: Any, timeout: float = 5.0
    ) -> tuple[Any, ...]:
        self.gets.append((address, args))
        if address not in self._responses:
            raise TimeoutError(
                f"MockOscClient: no response configured for '{address}'. "
                f"Call mock.when_get('{address}', <value>) first."
            )
        return self._responses[address]

    def send(self, address: str, *args: Any) -> None:
        self.sends.append((address, args))

    async def ping(self) -> bool:
        return True

    def add_listener(self, address: str, callback: Any) -> None:
        self._listeners[address].append(callback)

    def remove_listener(self, address: str, callback: Any) -> None:
        try:
            self._listeners[address].remove(callback)
        except ValueError:
            pass

    def simulate_event(self, address: str, *args: Any) -> None:
        """Fire all listeners registered on address, as if AbletonOSC sent an update."""
        for cb in list(self._listeners.get(address, [])):
            cb(address, *args)

    # -- Convenience assertion helpers --

    def assert_sent(self, address: str, args: tuple[Any, ...] | None = None) -> None:
        """Assert that send() was called with the given address (and optionally exact args).

        Args:
            address: The OSC address that must have been sent.
            args:    If provided, the exact tuple of arguments. Pass as a tuple, e.g.
                     ``mock.assert_sent("/live/song/set/tempo", (140.0,))``.
        """
        matching = [s for s in self.sends if s[0] == address]
        assert matching, f"Expected send to '{address}', got: {[s[0] for s in self.sends]}"
        if args is not None:
            assert any(
                s[1] == args for s in matching
            ), f"Expected send('{address}', {args}), got args: {[s[1] for s in matching]}"

    def assert_not_sent(self, address: str) -> None:
        """Assert that send() was never called with this address."""
        matching = [s for s in self.sends if s[0] == address]
        assert not matching, f"Expected no send to '{address}', but it was called"


# ---------------------------------------------------------------------------
# pytest fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MockOscClient:
    """Provide a fresh MockOscClient for each test."""
    return MockOscClient()


# ---------------------------------------------------------------------------
# MockAbletonOscServer — real UDP server for OscClient network tests
# ---------------------------------------------------------------------------


class MockAbletonOscServer:
    """A real UDP OSC server that mimics AbletonOSC for testing OscClient.

    It listens on listen_port (default 12000) for incoming OSC messages.
    For each message it receives, it looks up a pre-loaded response and
    sends it back to reply_host:reply_port (default 127.0.0.1:12001).

    Example::

        server = MockAbletonOscServer()
        server.add_response("/live/test", "ok")
        await server.start()
        # ... run test ...
        await server.stop()
    """

    def __init__(
        self,
        listen_port: int = TEST_SEND_PORT,
        reply_host: str = "127.0.0.1",
        reply_port: int = TEST_RECEIVE_PORT,
    ) -> None:
        self._listen_port = listen_port
        self._reply_host = reply_host
        self._reply_port = reply_port
        self._responses: dict[str, tuple[Any, ...]] = {}
        # All received messages: (address, args)
        self.received: list[tuple[str, tuple[Any, ...]]] = []
        self._transport: asyncio.BaseTransport | None = None
        self._reply_client = SimpleUDPClient(reply_host, reply_port)

    def add_response(self, address: str, *response_args: Any) -> None:
        """Pre-load a response for a given OSC address."""
        self._responses[address] = response_args

    def _handle(self, address: str, *args: Any) -> None:
        self.received.append((address, args))
        if address in self._responses:
            resp = self._responses[address]
            self._reply_client.send_message(address, list(resp) if resp else [])

    async def start(self) -> None:
        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self._handle)
        loop = asyncio.get_running_loop()
        server = AsyncIOOSCUDPServer(
            ("127.0.0.1", self._listen_port), dispatcher, loop
        )
        self._transport, _ = await server.create_serve_endpoint()

    async def stop(self) -> None:
        if self._transport:
            self._transport.close()
            self._transport = None


# ---------------------------------------------------------------------------
# Fixtures for OscClient network tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def mock_osc_server():
    """Start a MockAbletonOscServer and yield it, then stop."""
    server = MockAbletonOscServer(
        listen_port=TEST_SEND_PORT,
        reply_port=TEST_RECEIVE_PORT,
    )
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def osc_client(mock_osc_server: MockAbletonOscServer):
    """OscClient connected to the mock server on test ports."""
    client = OscClient(
        host="127.0.0.1",
        send_port=TEST_SEND_PORT,
        receive_port=TEST_RECEIVE_PORT,
    )
    await client.start()
    yield client
    await client.stop()


# ---------------------------------------------------------------------------
# Common mock session data
# ---------------------------------------------------------------------------


def setup_default_session(mock: MockOscClient) -> None:
    """Pre-load a realistic Ableton session into a MockOscClient."""
    mock.when_get("/live/test", "ok")
    mock.when_get("/live/song/get/tempo", 120.0)
    mock.when_get("/live/song/get/signature_numerator", 4)
    mock.when_get("/live/song/get/signature_denominator", 4)
    mock.when_get("/live/song/get/is_playing", 0)
    mock.when_get("/live/song/get/current_song_time", 0.0)
    mock.when_get("/live/song/get/loop", 0)
    mock.when_get("/live/song/get/loop_start", 0.0)
    mock.when_get("/live/song/get/loop_length", 4.0)
    mock.when_get("/live/song/get/num_tracks", 3)
    mock.when_get("/live/song/get/num_scenes", 4)
    mock.when_get("/live/song/get/track_names", "Drums", "Bass", "Lead")
    mock.when_get("/live/track/get/has_midi_input", 0, 1)  # all tracks MIDI by default
    mock.when_get("/live/song/get/scenes/name", "Intro", "Verse", "Chorus", "Outro")
    mock.when_get("/live/song/get/cue_points")  # empty
