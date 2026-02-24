"""Unit tests for track tools."""

from __future__ import annotations

import pytest

from ableosc.tools import track as track_tools
from tests.conftest import MockOscClient, setup_default_session

pytestmark = pytest.mark.unit


def _setup_track(mock: MockOscClient, track_index: int = 0) -> None:
    """Pre-load realistic responses for a single track.

    Responses do NOT include the track_index prefix — AbletonOSC returns
    just the value(s). This assumption will be validated via integration tests.
    """
    mock.when_get("/live/track/get/name", "Drums")
    mock.when_get("/live/track/get/volume", 0.85)
    mock.when_get("/live/track/get/panning", 0.0)
    mock.when_get("/live/track/get/mute", 0)
    mock.when_get("/live/track/get/solo", 0)
    mock.when_get("/live/track/get/arm", 1)
    mock.when_get("/live/track/get/can_be_armed", 1)
    mock.when_get("/live/track/get/num_devices", 1)
    mock.when_get("/live/track/get/devices/name", "Drum Rack")
    mock.when_get("/live/track/get/clips/name", "Beat Loop", None, None, None)


# ---------------------------------------------------------------------------
# get_tracks
# ---------------------------------------------------------------------------


async def test_get_tracks_returns_all_tracks(mock_client: MockOscClient):
    setup_default_session(mock_client)
    result = await track_tools.get_tracks(mock_client)

    assert result["count"] == 3
    assert len(result["tracks"]) == 3
    assert result["tracks"][0] == {"index": 0, "name": "Drums"}
    assert result["tracks"][1] == {"index": 1, "name": "Bass"}
    assert result["tracks"][2] == {"index": 2, "name": "Lead"}


async def test_get_tracks_empty_session(mock_client: MockOscClient):
    mock_client.when_get("/live/song/get/num_tracks", 0)
    mock_client.when_get("/live/song/get/track_names")  # empty
    result = await track_tools.get_tracks(mock_client)
    assert result["count"] == 0
    assert result["tracks"] == []


# ---------------------------------------------------------------------------
# get_track
# ---------------------------------------------------------------------------


async def test_get_track_returns_full_detail(mock_client: MockOscClient):
    _setup_track(mock_client, 0)
    result = await track_tools.get_track(mock_client, 0)

    assert result["index"] == 0
    assert result["name"] == "Drums"
    assert result["volume"] == 0.85
    assert result["pan"] == 0.0
    assert result["mute"] is False
    assert result["solo"] is False
    assert result["arm"] is True
    assert result["can_be_armed"] is True
    assert result["devices"] == ["Drum Rack"]
    assert result["num_devices"] == 1


async def test_get_track_filters_empty_clip_slots(mock_client: MockOscClient):
    """Clips with None name (empty slots) should not appear in clips list."""
    _setup_track(mock_client, 0)
    result = await track_tools.get_track(mock_client, 0)
    assert len(result["clips"]) == 1
    assert result["clips"][0]["name"] == "Beat Loop"


# ---------------------------------------------------------------------------
# Scalar helper — response parsing
# ---------------------------------------------------------------------------


def test_scalar_single_value():
    """_scalar should return args[0] for a 1-tuple."""
    assert track_tools._scalar((120.0,)) == 120.0


def test_scalar_returns_first_element():
    """_scalar always returns args[0] — the simple, no-index-skipping version.

    If AbletonOSC turns out to prepend track_index to responses, we'll add
    index-aware parsing here once confirmed via integration tests.
    """
    assert track_tools._scalar((0.85,)) == 0.85
    # For a 2-tuple, returns the first element (no special-casing)
    assert track_tools._scalar((0, 0.85)) == 0


def test_scalar_empty():
    assert track_tools._scalar(()) is None


# ---------------------------------------------------------------------------
# Volume / pan / mix
# ---------------------------------------------------------------------------


async def test_set_track_volume(mock_client: MockOscClient):
    result = await track_tools.set_track_volume(mock_client, 0, 0.75)
    assert result["status"] == "ok"
    assert result["volume"] == 0.75
    mock_client.assert_sent("/live/track/set/volume", (0, 0.75))


async def test_set_track_volume_rejects_out_of_range(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="0.0"):
        await track_tools.set_track_volume(mock_client, 0, 1.5)


async def test_set_track_pan_centre(mock_client: MockOscClient):
    result = await track_tools.set_track_pan(mock_client, 1, 0.0)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/track/set/panning", (1, 0.0))


async def test_set_track_pan_full_left(mock_client: MockOscClient):
    result = await track_tools.set_track_pan(mock_client, 0, -1.0)
    assert result["pan"] == -1.0


async def test_set_track_pan_rejects_out_of_range(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="-1.0"):
        await track_tools.set_track_pan(mock_client, 0, 2.0)


async def test_set_track_send(mock_client: MockOscClient):
    result = await track_tools.set_track_send(mock_client, 0, 0, 0.5)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/track/set/send", (0, 0, 0.5))


async def test_set_track_send_rejects_out_of_range(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="0.0"):
        await track_tools.set_track_send(mock_client, 0, 0, 1.5)


# ---------------------------------------------------------------------------
# Mute / solo / arm
# ---------------------------------------------------------------------------


async def test_set_track_mute_true(mock_client: MockOscClient):
    result = await track_tools.set_track_mute(mock_client, 0, True)
    assert result["mute"] is True
    mock_client.assert_sent("/live/track/set/mute", (0, 1))


async def test_set_track_mute_false(mock_client: MockOscClient):
    result = await track_tools.set_track_mute(mock_client, 0, False)
    mock_client.assert_sent("/live/track/set/mute", (0, 0))


async def test_set_track_solo(mock_client: MockOscClient):
    result = await track_tools.set_track_solo(mock_client, 2, True)
    assert result["solo"] is True
    mock_client.assert_sent("/live/track/set/solo", (2, 1))


async def test_set_track_arm(mock_client: MockOscClient):
    result = await track_tools.set_track_arm(mock_client, 0, True)
    assert result["arm"] is True
    mock_client.assert_sent("/live/track/set/arm", (0, 1))


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------


async def test_set_track_name(mock_client: MockOscClient):
    result = await track_tools.set_track_name(mock_client, 0, "Kick")
    assert result["name"] == "Kick"
    mock_client.assert_sent("/live/track/set/name", (0, "Kick"))


# ---------------------------------------------------------------------------
# Create / delete
# ---------------------------------------------------------------------------


async def test_create_midi_track(mock_client: MockOscClient):
    result = await track_tools.create_midi_track(mock_client)
    assert result["type"] == "midi"
    mock_client.assert_sent("/live/song/create_midi_track")


async def test_create_audio_track(mock_client: MockOscClient):
    result = await track_tools.create_audio_track(mock_client)
    assert result["type"] == "audio"
    mock_client.assert_sent("/live/song/create_audio_track")


async def test_create_return_track(mock_client: MockOscClient):
    result = await track_tools.create_return_track(mock_client)
    assert result["type"] == "return"
    mock_client.assert_sent("/live/song/create_return_track")


async def test_delete_track(mock_client: MockOscClient):
    result = await track_tools.delete_track(mock_client, 2)
    assert result["deleted_track_index"] == 2
    mock_client.assert_sent("/live/song/delete_track", (2,))


async def test_stop_track_clips(mock_client: MockOscClient):
    result = await track_tools.stop_track_clips(mock_client, 1)
    mock_client.assert_sent("/live/track/stop_all_clips", (1,))


async def test_duplicate_track(mock_client: MockOscClient):
    result = await track_tools.duplicate_track(mock_client, 0)
    mock_client.assert_sent("/live/song/duplicate_track", (0,))
