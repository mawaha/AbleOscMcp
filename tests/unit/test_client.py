"""Unit tests for OscClient — exercises the networking layer using MockAbletonOscServer."""

from __future__ import annotations

import asyncio

import pytest
from pytest import approx

from ableosc.client import OscClient
from tests.conftest import MockAbletonOscServer, TEST_SEND_PORT, TEST_RECEIVE_PORT


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ping
# ---------------------------------------------------------------------------


async def test_ping_succeeds_when_server_responds(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    mock_osc_server.add_response("/live/test", "ok")
    result = await osc_client.ping()
    assert result is True


async def test_ping_fails_when_no_server():
    """OscClient with no responding server should return False from ping."""
    # Use ports that nothing is listening on
    client = OscClient(host="127.0.0.1", send_port=19999, receive_port=19998)
    await client.start()
    try:
        result = await client.ping()
        assert result is False
    finally:
        await client.stop()


# ---------------------------------------------------------------------------
# get — request / response
# ---------------------------------------------------------------------------


async def test_get_single_value(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    mock_osc_server.add_response("/live/song/get/tempo", 128.0)
    result = await osc_client.get("/live/song/get/tempo")
    assert result == (128.0,)


async def test_get_multiple_values(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    mock_osc_server.add_response(
        "/live/song/get/track_names", "Drums", "Bass", "Lead"
    )
    result = await osc_client.get("/live/song/get/track_names")
    assert result == ("Drums", "Bass", "Lead")


async def test_get_with_args(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    """Sending args (e.g. track_index) should still work for request/response.

    NOTE: OSC uses 32-bit floats so values like 0.85 lose precision in transit.
    We use pytest.approx for float comparisons.
    """
    mock_osc_server.add_response("/live/track/get/volume", 0.85)
    result = await osc_client.get("/live/track/get/volume", 0)
    assert result == pytest.approx((0.85,), rel=1e-5)
    # Verify the server received the message with the track_index arg
    received = [r for r in mock_osc_server.received if r[0] == "/live/track/get/volume"]
    assert received, "Server should have received the request"
    assert received[0][1] == (0,), "Should have received track_index=0"


async def test_get_timeout(osc_client: OscClient):
    """get() should raise TimeoutError when no response arrives."""
    with pytest.raises(TimeoutError, match="AbletonOSC"):
        await osc_client.get("/live/nothing/here", timeout=0.1)


async def test_get_concurrent_different_addresses(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    """Concurrent GETs on different addresses should all resolve independently."""
    mock_osc_server.add_response("/live/song/get/tempo", 120.0)
    mock_osc_server.add_response("/live/song/get/signature_numerator", 4)
    mock_osc_server.add_response("/live/song/get/is_playing", 0)

    tempo, num, playing = await asyncio.gather(
        osc_client.get("/live/song/get/tempo"),
        osc_client.get("/live/song/get/signature_numerator"),
        osc_client.get("/live/song/get/is_playing"),
    )

    assert tempo == (120.0,)
    assert num == (4,)
    assert playing == (0,)


# ---------------------------------------------------------------------------
# send — fire and forget
# ---------------------------------------------------------------------------


async def test_send_delivers_message(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    osc_client.send("/live/song/start_playing")
    # Give the event loop a moment for the UDP packet to arrive
    await asyncio.sleep(0.05)
    received_addresses = [r[0] for r in mock_osc_server.received]
    assert "/live/song/start_playing" in received_addresses


async def test_send_with_args(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    osc_client.send("/live/song/set/tempo", 140.0)
    await asyncio.sleep(0.05)
    received = [r for r in mock_osc_server.received if r[0] == "/live/song/set/tempo"]
    assert received
    assert received[0][1] == (140.0,)


# ---------------------------------------------------------------------------
# Listeners
# ---------------------------------------------------------------------------


async def test_listener_receives_unsolicited_message(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    received_args: list[tuple] = []

    def on_tempo(address: str, *args):
        received_args.append(args)

    osc_client.add_listener("/live/song/get/tempo", on_tempo)

    # Simulate AbletonOSC pushing an update (e.g. from start_listen)
    mock_osc_server._reply_client.send_message("/live/song/get/tempo", [135.0])
    await asyncio.sleep(0.05)

    assert len(received_args) == 1
    assert received_args[0] == (135.0,)


async def test_listener_remove(
    osc_client: OscClient, mock_osc_server: MockAbletonOscServer
):
    received: list[tuple] = []

    def callback(address: str, *args):
        received.append(args)

    osc_client.add_listener("/live/song/get/tempo", callback)
    osc_client.remove_listener("/live/song/get/tempo", callback)

    mock_osc_server._reply_client.send_message("/live/song/get/tempo", [135.0])
    await asyncio.sleep(0.05)

    assert received == [], "Removed listener should not fire"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_get_raises_when_not_started():
    client = OscClient()
    with pytest.raises(RuntimeError, match="not running"):
        await client.get("/live/test")


async def test_send_raises_when_not_started():
    client = OscClient()
    with pytest.raises(RuntimeError, match="not running"):
        client.send("/live/test")
