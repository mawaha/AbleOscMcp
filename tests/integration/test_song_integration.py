"""Integration tests for song-level tools (transport, tempo, loop, cues)."""

from __future__ import annotations

import asyncio

import pytest

from ableosc.client import OscClient
from ableosc.tools import song as song_tools

pytestmark = pytest.mark.integration


async def test_set_tempo_round_trip(live_client: OscClient):
    original = await song_tools.get_session_info(live_client)
    original_tempo = original["tempo"]
    try:
        result = await song_tools.set_tempo(live_client, 142.0)
        assert result["status"] == "ok"

        info = await song_tools.get_session_info(live_client)
        assert abs(info["tempo"] - 142.0) < 0.5
    finally:
        await song_tools.set_tempo(live_client, original_tempo)


async def test_set_tempo_rejects_out_of_range(live_client: OscClient):
    with pytest.raises(ValueError):
        await song_tools.set_tempo(live_client, 5.0)
    with pytest.raises(ValueError):
        await song_tools.set_tempo(live_client, 1500.0)


async def test_start_and_stop_playing(live_client: OscClient):
    try:
        await song_tools.start_playing(live_client)
        await asyncio.sleep(0.1)
        info = await song_tools.get_session_info(live_client)
        assert info["is_playing"] is True
    finally:
        await song_tools.stop_playing(live_client)
        await asyncio.sleep(0.1)
        info = await song_tools.get_session_info(live_client)
        assert info["is_playing"] is False


async def test_set_loop_start_and_length(live_client: OscClient):
    # Note: song.loop (enabled toggle) is silently ignored by Ableton when the
    # arrangement view is not active. We verify loop_start and loop_length instead.
    original = await song_tools.get_session_info(live_client)
    try:
        result = await song_tools.set_loop(live_client, enabled=True, start_beats=2.0, length_beats=4.0)
        assert result["status"] == "ok"
        await asyncio.sleep(0.1)

        info = await song_tools.get_session_info(live_client)
        assert abs(info["loop"]["start_beats"] - 2.0) < 0.01
        assert abs(info["loop"]["length_beats"] - 4.0) < 0.01
    finally:
        await song_tools.set_loop(
            live_client,
            enabled=original["loop"]["enabled"],
            start_beats=original["loop"]["start_beats"],
            length_beats=original["loop"]["length_beats"],
        )


async def test_set_loop_disabled(live_client: OscClient):
    original = await song_tools.get_session_info(live_client)
    try:
        await song_tools.set_loop(live_client, enabled=False)
        info = await song_tools.get_session_info(live_client)
        assert info["loop"]["enabled"] is False
    finally:
        await song_tools.set_loop(
            live_client,
            enabled=original["loop"]["enabled"],
            start_beats=original["loop"]["start_beats"],
            length_beats=original["loop"]["length_beats"],
        )


async def test_get_cue_points_returns_list(live_client: OscClient):
    result = await song_tools.get_cue_points(live_client)
    assert "cue_points" in result
    assert isinstance(result["cue_points"], list)
    for cue in result["cue_points"]:
        assert "name" in cue
        assert "time" in cue


async def test_undo_and_redo_do_not_raise(live_client: OscClient):
    result = await song_tools.undo(live_client)
    assert result["status"] == "ok"
    result = await song_tools.redo(live_client)
    assert result["status"] == "ok"


async def test_tap_tempo_does_not_raise(live_client: OscClient):
    result = await song_tools.tap_tempo(live_client)
    assert result["status"] == "ok"
