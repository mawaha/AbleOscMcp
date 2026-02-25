"""Unit tests for real-time listener tools (subscribe, poll, unsubscribe)."""

from __future__ import annotations

import asyncio

import pytest

from ableosc.subscriptions import SubscriptionRegistry, build_addresses
from ableosc.tools import listen as listen_tools

from tests.conftest import MockOscClient


# ---------------------------------------------------------------------------
# build_addresses
# ---------------------------------------------------------------------------

def test_build_addresses_song():
    start, stop, get, args, n = build_addresses("song", "tempo")
    assert start == "/live/song/start_listen/tempo"
    assert stop == "/live/song/stop_listen/tempo"
    assert get == "/live/song/get/tempo"
    assert args == ()
    assert n == 0


def test_build_addresses_view():
    start, stop, get, args, n = build_addresses("view", "selected_track")
    assert start == "/live/view/start_listen/selected_track"
    assert get == "/live/view/get/selected_track"
    assert args == ()
    assert n == 0


def test_build_addresses_track():
    start, stop, get, args, n = build_addresses("track", "mute", track_index=2)
    assert start == "/live/track/start_listen/mute"
    assert args == (2,)
    assert n == 1


def test_build_addresses_track_missing_index():
    with pytest.raises(ValueError, match="track_index"):
        build_addresses("track", "mute")


def test_build_addresses_scene():
    start, stop, get, args, n = build_addresses("scene", "name", scene_index=0)
    assert args == (0,)
    assert n == 1


def test_build_addresses_clip():
    start, stop, get, args, n = build_addresses("clip", "is_playing", track_index=1, clip_index=3)
    assert args == (1, 3)
    assert n == 2


def test_build_addresses_clip_missing_clip_index():
    with pytest.raises(ValueError, match="clip_index"):
        build_addresses("clip", "is_playing", track_index=0)


def test_build_addresses_device():
    start, stop, get, args, n = build_addresses("device", "name", track_index=0, device_index=1)
    assert args == (0, 1)
    # Device listeners send (value,) — no index prefix in the response
    assert n == 0


def test_build_addresses_unknown_level():
    with pytest.raises(ValueError, match="Unknown level"):
        build_addresses("bogus", "tempo")


# ---------------------------------------------------------------------------
# subscribe
# ---------------------------------------------------------------------------

async def test_subscribe_song_sends_start_listen(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")

    assert "sub_id" in result
    assert result["status"] == "subscribed"
    assert result["response_address"] == "/live/song/get/tempo"
    mock_client.assert_sent("/live/song/start_listen/tempo", ())


async def test_subscribe_track_sends_start_listen_with_index(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    await listen_tools.subscribe(mock_client, registry, "mute", "track", track_index=3)
    mock_client.assert_sent("/live/track/start_listen/mute", (3,))


async def test_subscribe_clip_sends_start_listen_with_two_indices(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    await listen_tools.subscribe(mock_client, registry, "is_playing", "clip", track_index=1, clip_index=2)
    mock_client.assert_sent("/live/clip/start_listen/is_playing", (1, 2))


async def test_subscribe_registers_listener(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    assert len(mock_client._listeners["/live/song/get/tempo"]) == 1


async def test_subscribe_returns_unique_sub_ids(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    r1 = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    r2 = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    assert r1["sub_id"] != r2["sub_id"]


# ---------------------------------------------------------------------------
# poll
# ---------------------------------------------------------------------------

async def test_poll_returns_event_after_simulate(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    mock_client.simulate_event("/live/song/get/tempo", 128.0)

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0)
    assert polled["events"] == [{"value": 128.0}]
    assert polled["queued_remaining"] == 0


async def test_poll_drains_multiple_events(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    for bpm in [120.0, 130.0, 140.0]:
        mock_client.simulate_event("/live/song/get/tempo", bpm)

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0)
    assert len(polled["events"]) == 3
    assert [e["value"] for e in polled["events"]] == [120.0, 130.0, 140.0]


async def test_poll_respects_max_events(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    for i in range(10):
        mock_client.simulate_event("/live/song/get/tempo", float(i))

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0, max_events=3)
    assert len(polled["events"]) == 3
    assert polled["queued_remaining"] == 7


async def test_poll_returns_empty_on_timeout(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0.01)
    assert polled["events"] == []
    assert polled["queued_remaining"] == 0


async def test_poll_blocks_until_event_arrives(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    async def send_event_soon():
        await asyncio.sleep(0.05)
        mock_client.simulate_event("/live/song/get/tempo", 99.0)

    asyncio.ensure_future(send_event_soon())
    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=2.0)
    assert polled["events"] == [{"value": 99.0}]


async def test_poll_unknown_sub_id_raises(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    with pytest.raises(ValueError, match="Unknown subscription"):
        await listen_tools.poll(registry, "sub_doesnotexist")


async def test_poll_track_event_strips_index_prefix(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "mute", "track", track_index=2)
    sub_id = result["sub_id"]

    # AbletonOSC sends (track_index, value) for track-level listeners
    mock_client.simulate_event("/live/track/get/mute", 2, 1)

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0)
    assert polled["events"] == [{"value": 1}]


async def test_poll_clip_event_strips_two_index_prefix(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "is_playing", "clip", track_index=0, clip_index=1)
    sub_id = result["sub_id"]

    # AbletonOSC sends (track_index, clip_index, value) for clip-level listeners
    mock_client.simulate_event("/live/clip/get/is_playing", 0, 1, 1)

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0)
    assert polled["events"] == [{"value": 1}]


async def test_poll_device_event_no_index_prefix(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "name", "device", track_index=0, device_index=0)
    sub_id = result["sub_id"]

    # Device listeners send (value,) — no index prefix
    mock_client.simulate_event("/live/device/get/name", "Reverb")

    polled = await listen_tools.poll(registry, sub_id, timeout_seconds=0)
    assert polled["events"] == [{"value": "Reverb"}]


# ---------------------------------------------------------------------------
# unsubscribe
# ---------------------------------------------------------------------------

async def test_unsubscribe_sends_stop_listen(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    mock_client.reset_history()
    await listen_tools.unsubscribe(mock_client, registry, sub_id)

    mock_client.assert_sent("/live/song/stop_listen/tempo", ())


async def test_unsubscribe_removes_listener(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    await listen_tools.unsubscribe(mock_client, registry, sub_id)

    assert len(mock_client._listeners["/live/song/get/tempo"]) == 0


async def test_unsubscribe_removes_from_registry(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    sub_id = result["sub_id"]

    await listen_tools.unsubscribe(mock_client, registry, sub_id)

    assert registry.get(sub_id) is None


async def test_unsubscribe_unknown_raises(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    with pytest.raises(ValueError, match="Unknown subscription"):
        await listen_tools.unsubscribe(mock_client, registry, "sub_doesnotexist")


async def test_unsubscribe_track_sends_correct_args(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.subscribe(mock_client, registry, "mute", "track", track_index=5)
    sub_id = result["sub_id"]

    mock_client.reset_history()
    await listen_tools.unsubscribe(mock_client, registry, sub_id)

    mock_client.assert_sent("/live/track/stop_listen/mute", (5,))


# ---------------------------------------------------------------------------
# list_subscriptions
# ---------------------------------------------------------------------------

async def test_list_subscriptions_empty(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    result = await listen_tools.list_subscriptions(registry)
    assert result == {"subscriptions": []}


async def test_list_subscriptions_shows_active(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    r = await listen_tools.subscribe(mock_client, registry, "tempo", "song")

    result = await listen_tools.list_subscriptions(registry)
    assert len(result["subscriptions"]) == 1
    entry = result["subscriptions"][0]
    assert entry["sub_id"] == r["sub_id"]
    assert entry["response_address"] == "/live/song/get/tempo"
    assert entry["queued_events"] == 0


async def test_list_subscriptions_shows_queue_depth(mock_client: MockOscClient):
    registry = SubscriptionRegistry()
    r = await listen_tools.subscribe(mock_client, registry, "tempo", "song")
    mock_client.simulate_event("/live/song/get/tempo", 140.0)
    mock_client.simulate_event("/live/song/get/tempo", 150.0)

    result = await listen_tools.list_subscriptions(registry)
    assert result["subscriptions"][0]["queued_events"] == 2
