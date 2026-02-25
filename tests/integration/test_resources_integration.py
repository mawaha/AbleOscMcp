"""Integration tests for MCP resource builder functions.

Requires a live Ableton session with AbletonOSC active.
Run with: ABLEOSC_INTEGRATION=1 uv run pytest tests/integration/test_resources_integration.py -v
"""

from __future__ import annotations

import pytest

from ableosc import resources
from ableosc.client import OscClient
from ableosc.tools import track as track_tools

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# session_state
# ---------------------------------------------------------------------------


async def test_session_state_has_correct_field_types(live_client: OscClient):
    result = await resources.session_state(live_client)

    assert isinstance(result["tempo"], float)
    assert 20.0 <= result["tempo"] <= 999.0
    assert isinstance(result["time_signature"], str)
    assert "/" in result["time_signature"]
    assert isinstance(result["is_playing"], bool)
    assert isinstance(result["current_time_beats"], float)
    assert isinstance(result["num_tracks"], int)
    assert isinstance(result["num_scenes"], int)


async def test_session_state_includes_loop(live_client: OscClient):
    result = await resources.session_state(live_client)

    loop = result["loop"]
    assert isinstance(loop["enabled"], bool)
    assert isinstance(loop["start_beats"], float)
    assert isinstance(loop["length_beats"], float)
    assert loop["length_beats"] > 0.0


async def test_session_state_track_list_matches_num_tracks(live_client: OscClient):
    result = await resources.session_state(live_client)

    assert len(result["tracks"]) == result["num_tracks"]
    for i, track in enumerate(result["tracks"]):
        assert track["index"] == i
        assert isinstance(track["name"], str)


# ---------------------------------------------------------------------------
# session_tracks
# ---------------------------------------------------------------------------


async def test_session_tracks_count_matches_live_session(live_client: OscClient):
    track_list = await track_tools.get_tracks(live_client)
    result = await resources.session_tracks(live_client)

    assert result["count"] == track_list["count"]
    assert len(result["tracks"]) == track_list["count"]


async def test_session_tracks_each_has_required_fields(live_client: OscClient):
    result = await resources.session_tracks(live_client)

    for i, track in enumerate(result["tracks"]):
        assert track["index"] == i
        assert isinstance(track["name"], str)
        assert 0.0 <= track["volume"] <= 1.0
        assert -1.0 <= track["pan"] <= 1.0
        assert isinstance(track["mute"], bool)
        assert isinstance(track["solo"], bool)
        assert isinstance(track["arm"], bool)
        assert isinstance(track["can_be_armed"], bool)
        assert isinstance(track["devices"], list)
        assert isinstance(track["clips"], list)
        assert isinstance(track["num_devices"], int)


async def test_session_tracks_device_names_are_strings(live_client: OscClient):
    result = await resources.session_tracks(live_client)

    for track in result["tracks"]:
        for device_name in track["devices"]:
            assert isinstance(device_name, str)


async def test_session_tracks_clip_slots_have_index_and_name(live_client: OscClient):
    result = await resources.session_tracks(live_client)

    for track in result["tracks"]:
        for clip in track["clips"]:
            assert "slot_index" in clip
            assert isinstance(clip["slot_index"], int)
            assert isinstance(clip["name"], str)


# ---------------------------------------------------------------------------
# device_resource
# ---------------------------------------------------------------------------


async def _find_track_with_device(client: OscClient) -> tuple[int, int] | None:
    """Return (track_index, device_index=0) for the first track that has a device."""
    track_list = await track_tools.get_tracks(client)
    for i in range(track_list["count"]):
        track = await track_tools.get_track(client, i)
        if track["num_devices"] > 0:
            return i, 0
    return None


async def test_device_resource_returns_correct_structure(live_client: OscClient):
    location = await _find_track_with_device(live_client)
    if location is None:
        pytest.skip("No tracks with devices found in the current session")

    track_index, device_index = location
    result = await resources.device_resource(live_client, track_index, device_index)

    assert result["track_index"] == track_index
    assert result["device_index"] == device_index
    assert isinstance(result["device_name"], str)
    assert len(result["device_name"]) > 0
    assert isinstance(result["parameters"], list)
    assert isinstance(result["count"], int)
    assert result["count"] == len(result["parameters"])


async def test_device_resource_parameter_fields(live_client: OscClient):
    location = await _find_track_with_device(live_client)
    if location is None:
        pytest.skip("No tracks with devices found in the current session")

    track_index, device_index = location
    result = await resources.device_resource(live_client, track_index, device_index)

    if result["count"] == 0:
        pytest.skip("Device has no parameters")

    for i, param in enumerate(result["parameters"]):
        assert param["index"] == i
        assert isinstance(param["name"], str)
        assert isinstance(param["value"], float)
        assert isinstance(param["min"], float)
        assert isinstance(param["max"], float)
        assert isinstance(param["is_quantized"], bool)
        assert param["min"] <= param["max"]
