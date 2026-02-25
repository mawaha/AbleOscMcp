"""Integration tests for clip-level tools (create, notes, loop, fire/stop)."""

from __future__ import annotations

import pytest

from ableosc.client import OscClient
from ableosc.tools import clip as clip_tools
from ableosc.tools import track as track_tools

pytestmark = pytest.mark.integration

_C_MAJOR_SCALE = [
    {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100, "mute": 0},
    {"pitch": 62, "start_time": 1.0, "duration": 0.5, "velocity": 90,  "mute": 0},
    {"pitch": 64, "start_time": 2.0, "duration": 0.5, "velocity": 95,  "mute": 0},
    {"pitch": 65, "start_time": 3.0, "duration": 0.5, "velocity": 85,  "mute": 0},
]


# ---------------------------------------------------------------------------
# Clip creation / deletion
# ---------------------------------------------------------------------------

async def test_create_clip_appears_in_track(live_client: OscClient, midi_track: int):
    track_before = await track_tools.get_track(live_client, midi_track)
    assert not any(c["slot_index"] == 0 for c in track_before["clips"])

    await clip_tools.create_clip(live_client, midi_track, 0, length_beats=4.0)

    track_after = await track_tools.get_track(live_client, midi_track)
    assert any(c["slot_index"] == 0 for c in track_after["clips"])


async def test_delete_clip_removes_it(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    track_before = await track_tools.get_track(live_client, track_index)
    assert any(c["slot_index"] == clip_index for c in track_before["clips"])

    await clip_tools.delete_clip(live_client, track_index, clip_index)

    track_after = await track_tools.get_track(live_client, track_index)
    assert not any(c["slot_index"] == clip_index for c in track_after["clips"])


# ---------------------------------------------------------------------------
# get_clip_info field shapes
# ---------------------------------------------------------------------------

async def test_get_clip_info_returns_expected_fields(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    info = await clip_tools.get_clip_info(live_client, track_index, clip_index)
    assert isinstance(info["name"], str)
    assert info["length_beats"] == pytest.approx(4.0, abs=0.01)
    assert isinstance(info["looping"], bool)
    assert isinstance(info["is_playing"], bool)


# ---------------------------------------------------------------------------
# MIDI notes round-trip
# ---------------------------------------------------------------------------

async def test_add_notes_and_get_notes_round_trip(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await clip_tools.add_notes(live_client, track_index, clip_index, _C_MAJOR_SCALE)

    result = await clip_tools.get_notes(live_client, track_index, clip_index)
    assert result["count"] == len(_C_MAJOR_SCALE)

    pitches = {n["pitch"] for n in result["notes"]}
    assert pitches == {60, 62, 64, 65}


async def test_get_notes_empty_clip(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    result = await clip_tools.get_notes(live_client, track_index, clip_index)
    assert result["count"] == 0
    assert result["notes"] == []


async def test_remove_all_notes(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await clip_tools.add_notes(live_client, track_index, clip_index, _C_MAJOR_SCALE)

    await clip_tools.remove_notes(live_client, track_index, clip_index)

    result = await clip_tools.get_notes(live_client, track_index, clip_index)
    assert result["count"] == 0


async def test_remove_notes_by_pitch_range(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await clip_tools.add_notes(live_client, track_index, clip_index, _C_MAJOR_SCALE)

    # Remove only C (60) and D (62), keep E (64) and F (65)
    await clip_tools.remove_notes(live_client, track_index, clip_index, pitch_start=60, pitch_span=3)

    result = await clip_tools.get_notes(live_client, track_index, clip_index)
    remaining_pitches = {n["pitch"] for n in result["notes"]}
    assert 60 not in remaining_pitches
    assert 62 not in remaining_pitches
    assert 64 in remaining_pitches or 65 in remaining_pitches


# ---------------------------------------------------------------------------
# Clip properties
# ---------------------------------------------------------------------------

async def test_set_clip_name(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await clip_tools.set_clip_name(live_client, track_index, clip_index, "MyClip")
    info = await clip_tools.get_clip_info(live_client, track_index, clip_index)
    assert info["name"] == "MyClip"


async def test_set_clip_loop_settings(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await clip_tools.set_clip_loop(live_client, track_index, clip_index, looping=True, loop_start=0.0, loop_end=4.0)
    info = await clip_tools.get_clip_info(live_client, track_index, clip_index)
    assert info["looping"] is True
    assert info["loop_start_beats"] == pytest.approx(0.0, abs=0.01)
    assert info["loop_end_beats"] == pytest.approx(4.0, abs=0.01)


# ---------------------------------------------------------------------------
# Fire / stop
# ---------------------------------------------------------------------------

async def test_fire_and_stop_clip_do_not_raise(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    result = await clip_tools.fire_clip(live_client, track_index, clip_index)
    assert result["status"] == "ok"

    result = await clip_tools.stop_clip(live_client, track_index, clip_index)
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Duplicate loop
# ---------------------------------------------------------------------------

async def test_duplicate_clip_loop_doubles_notes(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await clip_tools.add_notes(live_client, track_index, clip_index, _C_MAJOR_SCALE)

    await clip_tools.duplicate_clip_loop(live_client, track_index, clip_index)

    result = await clip_tools.get_notes(live_client, track_index, clip_index)
    assert result["count"] == len(_C_MAJOR_SCALE) * 2
