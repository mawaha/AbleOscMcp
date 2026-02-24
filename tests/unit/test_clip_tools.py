"""Unit tests for clip tools."""

from __future__ import annotations

import pytest

from ableosc.tools import clip as clip_tools
from ableosc.tools.clip import _parse_notes, _flatten_notes
from tests.conftest import MockOscClient

pytestmark = pytest.mark.unit


def _setup_clip(mock: MockOscClient, track: int = 0, slot: int = 0) -> None:
    """Responses do NOT include track/clip index prefix."""
    mock.when_get("/live/clip/get/name", "My Clip")
    mock.when_get("/live/clip/get/length", 4.0)
    mock.when_get("/live/clip/get/looping", 1)
    mock.when_get("/live/clip/get/loop_start", 0.0)
    mock.when_get("/live/clip/get/loop_end", 4.0)
    mock.when_get("/live/clip/get/is_playing", 0)
    mock.when_get("/live/clip/get/color", 0xFF0000)


# ---------------------------------------------------------------------------
# Note parsing helpers
# ---------------------------------------------------------------------------


def test_parse_notes_empty():
    assert _parse_notes(()) == []


def test_parse_notes_single():
    # pitch=60, start=0.0, dur=0.25, vel=100, mute=0
    result = _parse_notes((60, 0.0, 0.25, 100, 0))
    assert result == [{"pitch": 60, "start_time": 0.0, "duration": 0.25, "velocity": 100, "mute": 0}]


def test_parse_notes_multiple():
    result = _parse_notes((60, 0.0, 0.25, 100, 0, 64, 0.5, 0.25, 90, 0))
    assert len(result) == 2
    assert result[0]["pitch"] == 60
    assert result[1]["pitch"] == 64
    assert result[1]["start_time"] == 0.5


def test_parse_notes_incomplete_trailing_ignored():
    """If the flat list isn't divisible by 5, trailing partial note is ignored."""
    # 7 values — 1 complete note + 2 orphan args
    result = _parse_notes((60, 0.0, 0.25, 100, 0, 64, 0.5))
    assert len(result) == 1


def test_flatten_notes_roundtrip():
    notes = [
        {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100, "mute": 0},
        {"pitch": 62, "start_time": 0.5, "duration": 0.5, "velocity": 80, "mute": 0},
    ]
    flat = _flatten_notes(notes)
    assert flat == [60, 0.0, 0.5, 100, 0, 62, 0.5, 0.5, 80, 0]
    # Round-trip
    parsed = _parse_notes(tuple(flat))
    assert parsed == notes


def test_flatten_notes_default_values():
    """Missing note fields should use sensible defaults."""
    notes = [{"pitch": 60}]
    flat = _flatten_notes(notes)
    assert flat[0] == 60          # pitch
    assert flat[1] == 0.0         # start_time default
    assert flat[2] == 0.25        # duration default
    assert flat[3] == 100         # velocity default
    assert flat[4] == 0           # mute default


# ---------------------------------------------------------------------------
# get_clip_info
# ---------------------------------------------------------------------------


async def test_get_clip_info(mock_client: MockOscClient):
    _setup_clip(mock_client)
    result = await clip_tools.get_clip_info(mock_client, 0, 0)

    assert result["name"] == "My Clip"
    assert result["length_beats"] == 4.0
    assert result["looping"] is True
    assert result["loop_start_beats"] == 0.0
    assert result["loop_end_beats"] == 4.0
    assert result["is_playing"] is False


# ---------------------------------------------------------------------------
# create / delete / fire / stop
# ---------------------------------------------------------------------------


async def test_create_clip(mock_client: MockOscClient):
    result = await clip_tools.create_clip(mock_client, 0, 0, length_beats=8.0)
    assert result["status"] == "ok"
    assert result["length_beats"] == 8.0
    mock_client.assert_sent("/live/clip_slot/create_clip", (0, 0, 8.0))


async def test_create_clip_default_length(mock_client: MockOscClient):
    result = await clip_tools.create_clip(mock_client, 0, 0)
    assert result["length_beats"] == 4.0


async def test_create_clip_rejects_zero_length(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="positive"):
        await clip_tools.create_clip(mock_client, 0, 0, length_beats=0.0)


async def test_delete_clip(mock_client: MockOscClient):
    result = await clip_tools.delete_clip(mock_client, 0, 2)
    mock_client.assert_sent("/live/clip_slot/delete_clip", (0, 2))


async def test_fire_clip(mock_client: MockOscClient):
    result = await clip_tools.fire_clip(mock_client, 1, 0)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/clip_slot/fire", (1, 0))


async def test_stop_clip(mock_client: MockOscClient):
    result = await clip_tools.stop_clip(mock_client, 1, 0)
    mock_client.assert_sent("/live/clip_slot/stop", (1, 0))


async def test_set_clip_name(mock_client: MockOscClient):
    result = await clip_tools.set_clip_name(mock_client, 0, 0, "Chorus Loop")
    assert result["name"] == "Chorus Loop"
    mock_client.assert_sent("/live/clip/set/name", (0, 0, "Chorus Loop"))


# ---------------------------------------------------------------------------
# Loop settings
# ---------------------------------------------------------------------------


async def test_set_clip_loop_enable(mock_client: MockOscClient):
    await clip_tools.set_clip_loop(mock_client, 0, 0, looping=True)
    mock_client.assert_sent("/live/clip/set/looping", (0, 0, 1))


async def test_set_clip_loop_with_points(mock_client: MockOscClient):
    await clip_tools.set_clip_loop(mock_client, 0, 0, looping=True, loop_start=1.0, loop_end=3.0)
    mock_client.assert_sent("/live/clip/set/loop_start", (0, 0, 1.0))
    mock_client.assert_sent("/live/clip/set/loop_end", (0, 0, 3.0))


async def test_set_clip_loop_without_points_does_not_send_them(mock_client: MockOscClient):
    await clip_tools.set_clip_loop(mock_client, 0, 0, looping=True)
    mock_client.assert_not_sent("/live/clip/set/loop_start")
    mock_client.assert_not_sent("/live/clip/set/loop_end")


# ---------------------------------------------------------------------------
# get_notes
# ---------------------------------------------------------------------------


async def test_get_notes_empty_clip(mock_client: MockOscClient):
    mock_client.when_get("/live/clip/get/notes")  # no args = empty
    result = await clip_tools.get_notes(mock_client, 0, 0)
    assert result["notes"] == []
    assert result["count"] == 0


async def test_get_notes_with_data(mock_client: MockOscClient):
    mock_client.when_get(
        "/live/clip/get/notes",
        # 3 notes: C4, E4, G4 — a C major chord held for 1 beat (no index prefix)
        60, 0.0, 1.0, 100, 0,
        64, 0.0, 1.0, 90, 0,
        67, 0.0, 1.0, 85, 0,
    )
    result = await clip_tools.get_notes(mock_client, 0, 0)
    assert result["count"] == 3
    assert result["notes"][0]["pitch"] == 60
    assert result["notes"][1]["pitch"] == 64
    assert result["notes"][2]["pitch"] == 67


# ---------------------------------------------------------------------------
# add_notes
# ---------------------------------------------------------------------------


async def test_add_notes_sends_flat_args(mock_client: MockOscClient):
    notes = [
        {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100, "mute": 0},
        {"pitch": 64, "start_time": 0.5, "duration": 0.5, "velocity": 90, "mute": 0},
    ]
    result = await clip_tools.add_notes(mock_client, 0, 0, notes)
    assert result["added_count"] == 2

    expected_args = (0, 0, 60, 0.0, 0.5, 100, 0, 64, 0.5, 0.5, 90, 0)
    mock_client.assert_sent("/live/clip/add/notes", expected_args)


async def test_add_notes_rejects_empty_list(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="empty"):
        await clip_tools.add_notes(mock_client, 0, 0, [])


# ---------------------------------------------------------------------------
# remove_notes
# ---------------------------------------------------------------------------


async def test_remove_notes_all(mock_client: MockOscClient):
    result = await clip_tools.remove_notes(mock_client, 0, 0)
    mock_client.assert_sent("/live/clip/remove/notes", (0, 0))


async def test_remove_notes_with_range(mock_client: MockOscClient):
    await clip_tools.remove_notes(
        mock_client, 0, 0,
        pitch_start=60, pitch_span=12,
        time_start=0.0, time_span=4.0
    )
    mock_client.assert_sent("/live/clip/remove/notes", (0, 0, 60, 12, 0.0, 4.0))


async def test_remove_notes_partial_range_uses_defaults(mock_client: MockOscClient):
    """Providing only pitch range should fill in default time range."""
    await clip_tools.remove_notes(mock_client, 0, 0, pitch_start=60, pitch_span=12)
    # Should have sent with default time args
    matching = [s for s in mock_client.sends if s[0] == "/live/clip/remove/notes"]
    assert matching
    args = matching[0][1]
    assert args[2] == 60   # pitch_start
    assert args[3] == 12   # pitch_span
    # time_start and time_span should be present (defaults)
    assert len(args) == 6


# ---------------------------------------------------------------------------
# duplicate_clip_loop
# ---------------------------------------------------------------------------


async def test_duplicate_clip_loop(mock_client: MockOscClient):
    result = await clip_tools.duplicate_clip_loop(mock_client, 0, 0)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/clip/duplicate_loop", (0, 0))
