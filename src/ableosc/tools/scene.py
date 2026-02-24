"""Scene tools: list, launch, create and configure Ableton scenes."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient


async def get_scenes(client: "OscClient") -> dict[str, Any]:
    """Get all scenes in the session."""
    num_result, names_result = await asyncio.gather(
        client.get("/live/song/get/num_scenes"),
        client.get("/live/song/get/scenes/name"),
    )
    num_scenes = num_result[0]
    names = list(names_result)
    scenes = [
        {"index": i, "name": names[i] if i < len(names) else ""}
        for i in range(num_scenes)
    ]
    return {"scenes": scenes, "count": num_scenes}


async def get_scene(client: "OscClient", scene_index: int) -> dict[str, Any]:
    """Get detailed information about a single scene."""
    name, tempo, tempo_enabled = await asyncio.gather(
        client.get("/live/scene/get/name", scene_index),
        client.get("/live/scene/get/tempo", scene_index),
        client.get("/live/scene/get/tempo_enabled", scene_index),
    )
    return {
        "index": scene_index,
        "name": _scalar(name),
        "tempo": _scalar(tempo),
        "tempo_enabled": bool(_scalar(tempo_enabled)),
    }


async def fire_scene(client: "OscClient", scene_index: int) -> dict[str, Any]:
    """Launch all clips in a scene."""
    client.send("/live/scene/fire", scene_index)
    return {"status": "ok", "scene_index": scene_index}


async def create_scene(client: "OscClient") -> dict[str, str]:
    """Create a new empty scene at the end of the session."""
    client.send("/live/song/create_scene")
    return {"status": "ok"}


async def delete_scene(client: "OscClient", scene_index: int) -> dict[str, Any]:
    """Delete a scene."""
    client.send("/live/song/delete_scene", scene_index)
    return {"status": "ok", "deleted_scene_index": scene_index}


async def duplicate_scene(client: "OscClient", scene_index: int) -> dict[str, Any]:
    """Duplicate a scene."""
    client.send("/live/song/duplicate_scene", scene_index)
    return {"status": "ok", "duplicated_scene_index": scene_index}


async def set_scene_name(
    client: "OscClient", scene_index: int, name: str
) -> dict[str, Any]:
    """Rename a scene."""
    client.send("/live/scene/set/name", scene_index, name)
    return {"status": "ok", "scene_index": scene_index, "name": name}


async def set_scene_tempo(
    client: "OscClient", scene_index: int, tempo: float, enabled: bool = True
) -> dict[str, Any]:
    """Set a tempo override on a scene."""
    if not (20.0 <= tempo <= 999.0):
        raise ValueError(f"Tempo must be between 20 and 999 BPM, got {tempo}")
    client.send("/live/scene/set/tempo", scene_index, tempo)
    client.send("/live/scene/set/tempo_enabled", scene_index, int(enabled))
    return {"status": "ok", "scene_index": scene_index, "tempo": tempo, "enabled": enabled}


async def fire_selected_scene(client: "OscClient") -> dict[str, str]:
    """Launch whichever scene is currently selected in Live's UI."""
    client.send("/live/scene/fire_selected")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar(args: tuple[Any, ...]) -> Any:
    """Extract the value from a scene-level OSC response.

    AbletonOSC prefixes scene-level responses with scene_index:
        (scene_index, value)
    The value is always the last element.
    """
    return args[-1] if args else None
