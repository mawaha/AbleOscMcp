"""Integration tests — verify basic connectivity and response formats against real AbletonOSC."""

from __future__ import annotations

import pytest

from ableosc.client import OscClient
from ableosc.tools import song as song_tools
from ableosc.tools import track as track_tools

pytestmark = pytest.mark.integration


async def test_ping(live_client: OscClient):
    assert await live_client.ping() is True


async def test_get_session_info_returns_valid_data(live_client: OscClient):
    result = await song_tools.get_session_info(live_client)
    assert 20.0 <= result["tempo"] <= 999.0
    assert "/" in result["time_signature"]
    assert isinstance(result["is_playing"], bool)
    assert result["num_tracks"] >= 0
    assert result["num_scenes"] >= 0


async def test_get_tracks_returns_list(live_client: OscClient):
    result = await track_tools.get_tracks(live_client)
    assert isinstance(result["tracks"], list)
    assert result["count"] == len(result["tracks"])
    for track in result["tracks"]:
        assert "index" in track
        assert "name" in track
