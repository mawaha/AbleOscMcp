"""MCP resource builder functions.

Each function takes an OscClient and returns a structured dict.
They are called by resource closures in server.py and tested independently.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient

from ableosc.tools import device as device_tools
from ableosc.tools import song as song_tools
from ableosc.tools import track as track_tools


async def session_state(client: "OscClient") -> dict[str, Any]:
    """Snapshot of the current session: tempo, playback, loop, track names."""
    info = await song_tools.get_session_info(client)
    tracks = await track_tools.get_tracks(client)
    info["tracks"] = tracks["tracks"]
    return info


async def session_tracks(client: "OscClient") -> dict[str, Any]:
    """Full detail for all tracks gathered in parallel."""
    track_list = await track_tools.get_tracks(client)
    details = await asyncio.gather(*[
        track_tools.get_track(client, i)
        for i in range(track_list["count"])
    ])
    return {"tracks": list(details), "count": track_list["count"]}


async def device_resource(
    client: "OscClient", track_index: int, device_index: int
) -> dict[str, Any]:
    """All parameters for one device."""
    return await device_tools.get_device_parameters(client, track_index, device_index)
