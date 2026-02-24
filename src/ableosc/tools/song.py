"""Song-level tools: session state, transport, tempo, undo, cue points."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient


async def get_session_info(client: "OscClient") -> dict[str, Any]:
    """Get a snapshot of the current Ableton session state."""
    (
        tempo,
        num,
        denom,
        is_playing,
        current_time,
        loop,
        loop_start,
        loop_length,
        num_tracks,
        num_scenes,
    ) = await asyncio.gather(
        client.get("/live/song/get/tempo"),
        client.get("/live/song/get/signature_numerator"),
        client.get("/live/song/get/signature_denominator"),
        client.get("/live/song/get/is_playing"),
        client.get("/live/song/get/current_song_time"),
        client.get("/live/song/get/loop"),
        client.get("/live/song/get/loop_start"),
        client.get("/live/song/get/loop_length"),
        client.get("/live/song/get/num_tracks"),
        client.get("/live/song/get/num_scenes"),
    )
    return {
        "tempo": tempo[0],
        "time_signature": f"{num[0]}/{denom[0]}",
        "is_playing": bool(is_playing[0]),
        "current_time_beats": current_time[0],
        "loop": {
            "enabled": bool(loop[0]),
            "start_beats": loop_start[0],
            "length_beats": loop_length[0],
        },
        "num_tracks": num_tracks[0],
        "num_scenes": num_scenes[0],
    }


async def set_tempo(client: "OscClient", tempo: float) -> dict[str, Any]:
    """Set the session tempo in BPM."""
    if not (20.0 <= tempo <= 999.0):
        raise ValueError(f"Tempo must be between 20 and 999 BPM, got {tempo}")
    client.send("/live/song/set/tempo", tempo)
    return {"status": "ok", "tempo": tempo}


async def start_playing(client: "OscClient") -> dict[str, str]:
    """Start global transport playback."""
    client.send("/live/song/start_playing")
    return {"status": "ok"}


async def stop_playing(client: "OscClient") -> dict[str, str]:
    """Stop global transport playback."""
    client.send("/live/song/stop_playing")
    return {"status": "ok"}


async def stop_all_clips(client: "OscClient") -> dict[str, str]:
    """Stop all currently playing clips."""
    client.send("/live/song/stop_all_clips")
    return {"status": "ok"}


async def tap_tempo(client: "OscClient") -> dict[str, str]:
    """Send a tap-tempo pulse."""
    client.send("/live/song/tap_tempo")
    return {"status": "ok"}


async def undo(client: "OscClient") -> dict[str, str]:
    """Undo the last action in Ableton Live."""
    client.send("/live/song/undo")
    return {"status": "ok"}


async def redo(client: "OscClient") -> dict[str, str]:
    """Redo the last undone action in Ableton Live."""
    client.send("/live/song/redo")
    return {"status": "ok"}


async def set_loop(
    client: "OscClient",
    enabled: bool,
    start_beats: float | None = None,
    length_beats: float | None = None,
) -> dict[str, Any]:
    """Configure the session loop."""
    client.send("/live/song/set/loop", int(enabled))
    if start_beats is not None:
        client.send("/live/song/set/loop_start", start_beats)
    if length_beats is not None:
        client.send("/live/song/set/loop_length", length_beats)
    return {"status": "ok", "loop_enabled": enabled}


async def get_cue_points(client: "OscClient") -> dict[str, Any]:
    """Get all cue points in the session."""
    result = await client.get("/live/song/get/cue_points")
    # AbletonOSC returns a flat tuple: (name, time, name, time, ...)
    cue_points = []
    args = list(result)
    for i in range(0, len(args) - 1, 2):
        cue_points.append({"name": args[i], "time_beats": args[i + 1]})
    return {"cue_points": cue_points}


async def jump_to_cue(client: "OscClient", name_or_index: str | int) -> dict[str, str]:
    """Jump playback to a cue point by name or index."""
    client.send("/live/song/cue_point/jump", name_or_index)
    return {"status": "ok"}


async def capture_scene(client: "OscClient") -> dict[str, str]:
    """Capture currently playing clips into a new scene."""
    client.send("/live/song/capture_and_insert_scene")
    return {"status": "ok"}


async def trigger_session_record(client: "OscClient") -> dict[str, str]:
    """Toggle session record."""
    client.send("/live/song/trigger_session_record")
    return {"status": "ok"}
