"""View tools: navigate Live's UI selection (selected track, scene, clip, device)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient


async def get_selected_track(client: "OscClient") -> dict[str, Any]:
    """Get the index of the currently selected track."""
    result = await client.get("/live/view/get/selected_track")
    return {"selected_track_index": result[0]}


async def set_selected_track(client: "OscClient", track_index: int) -> dict[str, Any]:
    """Select a track in Live's UI."""
    client.send("/live/view/set/selected_track", track_index)
    return {"status": "ok", "selected_track_index": track_index}


async def get_selected_scene(client: "OscClient") -> dict[str, Any]:
    """Get the index of the currently selected scene."""
    result = await client.get("/live/view/get/selected_scene")
    return {"selected_scene_index": result[0]}


async def set_selected_scene(client: "OscClient", scene_index: int) -> dict[str, Any]:
    """Select a scene in Live's UI."""
    client.send("/live/view/set/selected_scene", scene_index)
    return {"status": "ok", "selected_scene_index": scene_index}


async def get_selected_clip(client: "OscClient") -> dict[str, Any]:
    """Get the track and scene index of the currently selected clip."""
    result = await client.get("/live/view/get/selected_clip")
    # Returns (track_index, scene_index)
    return {
        "selected_track_index": result[0] if len(result) > 0 else None,
        "selected_clip_index": result[1] if len(result) > 1 else None,
    }


async def set_selected_clip(
    client: "OscClient", track_index: int, clip_index: int
) -> dict[str, Any]:
    """Select a specific clip slot in Live's UI."""
    client.send("/live/view/set/selected_clip", track_index, clip_index)
    return {
        "status": "ok",
        "selected_track_index": track_index,
        "selected_clip_index": clip_index,
    }


async def get_selected_device(client: "OscClient") -> dict[str, Any]:
    """Get the track and device index of the currently selected device."""
    result = await client.get("/live/view/get/selected_device")
    # Returns (track_index, device_index)
    return {
        "selected_track_index": result[0] if len(result) > 0 else None,
        "selected_device_index": result[1] if len(result) > 1 else None,
    }


async def set_selected_device(
    client: "OscClient", track_index: int, device_index: int
) -> dict[str, Any]:
    """Select a device in Live's UI."""
    client.send("/live/view/set/selected_device", track_index, device_index)
    return {
        "status": "ok",
        "selected_track_index": track_index,
        "selected_device_index": device_index,
    }
