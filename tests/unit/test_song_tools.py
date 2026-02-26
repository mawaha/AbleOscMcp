"""Unit tests for song-level tools."""

from __future__ import annotations

import pytest

from ableosc.tools import song as song_tools
from tests.conftest import MockOscClient, setup_default_session

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# get_session_info
# ---------------------------------------------------------------------------


async def test_get_session_info_returns_full_snapshot(mock_client: MockOscClient):
    setup_default_session(mock_client)
    result = await song_tools.get_session_info(mock_client)

    assert result["tempo"] == 120.0
    assert result["time_signature"] == "4/4"
    assert result["is_playing"] is False
    assert result["current_time_beats"] == 0.0
    assert result["loop"]["enabled"] is False
    assert result["loop"]["start_beats"] == 0.0
    assert result["loop"]["length_beats"] == 4.0
    assert result["num_tracks"] == 3
    assert result["num_scenes"] == 4


async def test_get_session_info_is_playing_true(mock_client: MockOscClient):
    setup_default_session(mock_client)
    mock_client.when_get("/live/song/get/is_playing", 1)
    result = await song_tools.get_session_info(mock_client)
    assert result["is_playing"] is True


async def test_get_session_info_non_standard_time_signature(mock_client: MockOscClient):
    setup_default_session(mock_client)
    mock_client.when_get("/live/song/get/signature_numerator", 7)
    mock_client.when_get("/live/song/get/signature_denominator", 8)
    result = await song_tools.get_session_info(mock_client)
    assert result["time_signature"] == "7/8"


# ---------------------------------------------------------------------------
# set_tempo
# ---------------------------------------------------------------------------


async def test_set_tempo_sends_correct_osc(mock_client: MockOscClient):
    result = await song_tools.set_tempo(mock_client, 140.0)
    assert result["status"] == "ok"
    assert result["tempo"] == 140.0
    mock_client.assert_sent("/live/song/set/tempo", (140.0,))


async def test_set_tempo_rejects_out_of_range_low(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="20"):
        await song_tools.set_tempo(mock_client, 10.0)


async def test_set_tempo_rejects_out_of_range_high(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="999"):
        await song_tools.set_tempo(mock_client, 1000.0)


async def test_set_tempo_boundary_low(mock_client: MockOscClient):
    result = await song_tools.set_tempo(mock_client, 20.0)
    assert result["status"] == "ok"


async def test_set_tempo_boundary_high(mock_client: MockOscClient):
    result = await song_tools.set_tempo(mock_client, 999.0)
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Transport controls
# ---------------------------------------------------------------------------


async def test_start_playing(mock_client: MockOscClient):
    result = await song_tools.start_playing(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/start_playing")


async def test_stop_playing(mock_client: MockOscClient):
    result = await song_tools.stop_playing(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/stop_playing")


async def test_stop_all_clips(mock_client: MockOscClient):
    result = await song_tools.stop_all_clips(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/stop_all_clips")


async def test_tap_tempo(mock_client: MockOscClient):
    result = await song_tools.tap_tempo(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/tap_tempo")


async def test_undo(mock_client: MockOscClient):
    result = await song_tools.undo(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/undo")


async def test_redo(mock_client: MockOscClient):
    result = await song_tools.redo(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/redo")


# ---------------------------------------------------------------------------
# set_loop
# ---------------------------------------------------------------------------


async def test_set_loop_enable(mock_client: MockOscClient):
    result = await song_tools.set_loop(mock_client, enabled=True)
    assert result["loop_enabled"] is True
    mock_client.assert_sent("/live/song/set/loop", (1,))


async def test_set_loop_disable(mock_client: MockOscClient):
    result = await song_tools.set_loop(mock_client, enabled=False)
    assert result["loop_enabled"] is False
    mock_client.assert_sent("/live/song/set/loop", (0,))


async def test_set_loop_with_start_and_length(mock_client: MockOscClient):
    await song_tools.set_loop(mock_client, enabled=True, start_beats=8.0, length_beats=16.0)
    mock_client.assert_sent("/live/song/set/loop_start", (8.0,))
    mock_client.assert_sent("/live/song/set/loop_length", (16.0,))


async def test_set_loop_without_optional_args_does_not_send_them(mock_client: MockOscClient):
    await song_tools.set_loop(mock_client, enabled=True)
    mock_client.assert_not_sent("/live/song/set/loop_start")
    mock_client.assert_not_sent("/live/song/set/loop_length")


# ---------------------------------------------------------------------------
# get_cue_points
# ---------------------------------------------------------------------------


async def test_get_cue_points_empty(mock_client: MockOscClient):
    mock_client.when_get("/live/song/get/cue_points")  # empty response
    result = await song_tools.get_cue_points(mock_client)
    assert result["cue_points"] == []


async def test_get_cue_points_with_data(mock_client: MockOscClient):
    mock_client.when_get(
        "/live/song/get/cue_points",
        "Intro", 0.0, "Verse", 16.0, "Chorus", 32.0
    )
    result = await song_tools.get_cue_points(mock_client)
    cues = result["cue_points"]
    assert len(cues) == 3
    assert cues[0] == {"name": "Intro", "time_beats": 0.0}
    assert cues[1] == {"name": "Verse", "time_beats": 16.0}
    assert cues[2] == {"name": "Chorus", "time_beats": 32.0}


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


async def test_jump_to_cue_by_name(mock_client: MockOscClient):
    result = await song_tools.jump_to_cue(mock_client, "Chorus")
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/cue_point/jump", ("Chorus",))


async def test_jump_to_cue_by_index(mock_client: MockOscClient):
    result = await song_tools.jump_to_cue(mock_client, 2)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/cue_point/jump", (2,))


async def test_capture_scene(mock_client: MockOscClient):
    result = await song_tools.capture_scene(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/capture_and_insert_scene")


async def test_trigger_session_record(mock_client: MockOscClient):
    result = await song_tools.trigger_session_record(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/trigger_session_record")


async def test_save_project_returns_saved_true(monkeypatch):
    import subprocess
    import sys

    monkeypatch.setattr(sys, "platform", "darwin")

    class FakeResult:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    result = await song_tools.save_project()
    assert result["saved"] is True


async def test_save_project_unsupported_platform(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "platform", "win32")
    result = await song_tools.save_project()
    assert result["saved"] is False
    assert "error" in result
