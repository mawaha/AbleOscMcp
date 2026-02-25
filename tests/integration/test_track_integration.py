"""Integration tests for track-level tools (CRUD, properties)."""

from __future__ import annotations

import asyncio

import pytest

from ableosc.client import OscClient
from ableosc.tools import track as track_tools

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Track creation / deletion
# ---------------------------------------------------------------------------

async def test_create_midi_track_increases_count(live_client: OscClient):
    before = await track_tools.get_tracks(live_client)
    await track_tools.create_midi_track(live_client)
    await asyncio.sleep(0.1)
    after = await track_tools.get_tracks(live_client)
    assert after["count"] == before["count"] + 1
    # cleanup
    await track_tools.delete_track(live_client, after["count"] - 1)


async def test_create_audio_track_increases_count(live_client: OscClient):
    before = await track_tools.get_tracks(live_client)
    await track_tools.create_audio_track(live_client)
    await asyncio.sleep(0.1)
    after = await track_tools.get_tracks(live_client)
    assert after["count"] == before["count"] + 1
    # cleanup
    await track_tools.delete_track(live_client, after["count"] - 1)


async def test_delete_track_decreases_count(live_client: OscClient, midi_track: int):
    before = await track_tools.get_tracks(live_client)
    await track_tools.delete_track(live_client, midi_track)
    await asyncio.sleep(0.1)
    after = await track_tools.get_tracks(live_client)
    assert after["count"] == before["count"] - 1


# ---------------------------------------------------------------------------
# get_track field shapes
# ---------------------------------------------------------------------------

async def test_get_track_returns_expected_fields(live_client: OscClient, midi_track: int):
    result = await track_tools.get_track(live_client, midi_track)
    assert result["index"] == midi_track
    assert isinstance(result["name"], str)
    assert 0.0 <= result["volume"] <= 1.0
    assert -1.0 <= result["pan"] <= 1.0
    assert isinstance(result["mute"], bool)
    assert isinstance(result["solo"], bool)
    assert isinstance(result["arm"], bool)
    assert isinstance(result["can_be_armed"], bool)
    assert isinstance(result["devices"], list)
    assert isinstance(result["clips"], list)


# ---------------------------------------------------------------------------
# Property setters — set then read back via get_track
# ---------------------------------------------------------------------------

async def test_set_track_name(live_client: OscClient, midi_track: int):
    await track_tools.set_track_name(live_client, midi_track, "IntegrationTest")
    result = await track_tools.get_track(live_client, midi_track)
    assert result["name"] == "IntegrationTest"


async def test_set_track_volume(live_client: OscClient, midi_track: int):
    await track_tools.set_track_volume(live_client, midi_track, 0.5)
    result = await track_tools.get_track(live_client, midi_track)
    assert abs(result["volume"] - 0.5) < 0.01


async def test_set_track_volume_rejects_out_of_range(live_client: OscClient, midi_track: int):
    with pytest.raises(ValueError):
        await track_tools.set_track_volume(live_client, midi_track, 1.5)


async def test_set_track_pan(live_client: OscClient, midi_track: int):
    await track_tools.set_track_pan(live_client, midi_track, -0.5)
    result = await track_tools.get_track(live_client, midi_track)
    assert abs(result["pan"] - (-0.5)) < 0.01


async def test_set_track_pan_rejects_out_of_range(live_client: OscClient, midi_track: int):
    with pytest.raises(ValueError):
        await track_tools.set_track_pan(live_client, midi_track, 2.0)


async def test_set_track_mute_on_and_off(live_client: OscClient, midi_track: int):
    await track_tools.set_track_mute(live_client, midi_track, True)
    result = await track_tools.get_track(live_client, midi_track)
    assert result["mute"] is True

    await track_tools.set_track_mute(live_client, midi_track, False)
    result = await track_tools.get_track(live_client, midi_track)
    assert result["mute"] is False


async def test_set_track_arm_on_and_off(live_client: OscClient, midi_track: int):
    result = await track_tools.get_track(live_client, midi_track)
    if not result["can_be_armed"]:
        pytest.skip("Track cannot be armed")

    await track_tools.set_track_arm(live_client, midi_track, True)
    result = await track_tools.get_track(live_client, midi_track)
    assert result["arm"] is True

    await track_tools.set_track_arm(live_client, midi_track, False)
    result = await track_tools.get_track(live_client, midi_track)
    assert result["arm"] is False
