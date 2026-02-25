"""Integration tests for view/selection tools."""

from __future__ import annotations

import pytest

from ableosc.client import OscClient
from ableosc.tools import view as view_tools
from ableosc.tools import track as track_tools

pytestmark = pytest.mark.integration


async def test_set_and_get_selected_track(live_client: OscClient):
    tracks = await track_tools.get_tracks(live_client)
    if tracks["count"] == 0:
        pytest.skip("No tracks in session")

    target = tracks["count"] - 1
    await view_tools.set_selected_track(live_client, target)
    result = await view_tools.get_selected_track(live_client)
    assert result["selected_track_index"] == target


async def test_set_and_get_selected_scene(live_client: OscClient):
    await view_tools.set_selected_scene(live_client, 0)
    result = await view_tools.get_selected_scene(live_client)
    assert result["selected_scene_index"] == 0


async def test_get_selected_track_returns_valid_index(live_client: OscClient):
    tracks = await track_tools.get_tracks(live_client)
    result = await view_tools.get_selected_track(live_client)
    assert 0 <= result["selected_track_index"] < tracks["count"]


async def test_set_and_get_selected_clip(live_client: OscClient, midi_clip: tuple[int, int]):
    track_index, clip_index = midi_clip
    await view_tools.set_selected_clip(live_client, track_index, clip_index)
    result = await view_tools.get_selected_clip(live_client)
    assert result["selected_track_index"] == track_index
    assert result["selected_clip_index"] == clip_index
