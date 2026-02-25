"""Integration test fixtures — require a live Ableton + AbletonOSC instance."""

from __future__ import annotations

import asyncio
import os

import pytest

from ableosc.client import OscClient
from ableosc.tools import clip as clip_tools
from ableosc.tools import track as track_tools

# Skip all integration tests unless explicitly enabled
if not os.getenv("ABLEOSC_INTEGRATION"):
    pytest.skip(
        "Set ABLEOSC_INTEGRATION=1 to run integration tests against Ableton Live",
        allow_module_level=True,
    )


@pytest.fixture(scope="function")
async def live_client():
    """Real OscClient connected to Ableton Live with AbletonOSC."""
    client = OscClient(
        host=os.getenv("ABLEOSC_HOST", "127.0.0.1"),
        send_port=int(os.getenv("ABLEOSC_SEND_PORT", "11000")),
        receive_port=int(os.getenv("ABLEOSC_RECEIVE_PORT", "11001")),
    )
    await client.start()

    alive = await client.ping()
    if not alive:
        pytest.skip("AbletonOSC did not respond. Is Ableton Live running?")

    yield client
    await client.stop()


@pytest.fixture()
async def midi_track(live_client: OscClient):
    """Create a temporary MIDI track; yield its index; delete it on teardown."""
    before = await track_tools.get_tracks(live_client)
    expected_index = before["count"]

    await track_tools.create_midi_track(live_client)
    await asyncio.sleep(0.1)

    tracks = await track_tools.get_tracks(live_client)
    assert tracks["count"] == expected_index + 1, "MIDI track was not created"

    yield expected_index

    try:
        await track_tools.delete_track(live_client, expected_index)
        await asyncio.sleep(0.05)
    except Exception:
        pass  # best-effort cleanup


@pytest.fixture()
async def midi_clip(live_client: OscClient, midi_track: int):
    """Create an empty MIDI clip on midi_track slot 0; yield (track_index, clip_index)."""
    await clip_tools.create_clip(live_client, midi_track, 0, length_beats=4.0)
    await asyncio.sleep(0.1)
    yield midi_track, 0
    # clip is removed automatically when midi_track fixture deletes the track
