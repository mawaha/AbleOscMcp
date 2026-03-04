"""Track-level tools: properties, routing, creation, deletion."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient


async def get_tracks(client: "OscClient") -> dict[str, Any]:
    """Get a summary list of all tracks in the session."""
    num_result, names_result = await asyncio.gather(
        client.get("/live/song/get/num_tracks"),
        client.get("/live/song/get/track_names"),
    )
    num_tracks = num_result[0]
    names = list(names_result)  # flat tuple of track names

    if num_tracks == 0:
        return {"tracks": [], "count": 0}

    midi_r, vol_r, pan_r, mute_r, solo_r = await asyncio.gather(
        asyncio.gather(*[client.get("/live/track/get/has_midi_input", i) for i in range(num_tracks)]),
        asyncio.gather(*[client.get("/live/track/get/volume", i) for i in range(num_tracks)]),
        asyncio.gather(*[client.get("/live/track/get/panning", i) for i in range(num_tracks)]),
        asyncio.gather(*[client.get("/live/track/get/mute", i) for i in range(num_tracks)]),
        asyncio.gather(*[client.get("/live/track/get/solo", i) for i in range(num_tracks)]),
    )

    tracks = [
        {
            "index": i,
            "name": names[i] if i < len(names) else "?",
            "is_midi": bool(_scalar(midi_r[i])),
            "volume": _scalar(vol_r[i]),
            "pan": _scalar(pan_r[i]),
            "mute": bool(_scalar(mute_r[i])),
            "solo": bool(_scalar(solo_r[i])),
        }
        for i in range(num_tracks)
    ]
    return {"tracks": tracks, "count": num_tracks}


async def get_track(client: "OscClient", track_index: int) -> dict[str, Any]:
    """Get detailed information about a single track."""
    (
        name,
        volume,
        pan,
        mute,
        solo,
        arm,
        can_be_armed,
        is_midi,
        num_devices,
        device_names,
        clip_names,
    ) = await asyncio.gather(
        client.get("/live/track/get/name", track_index),
        client.get("/live/track/get/volume", track_index),
        client.get("/live/track/get/panning", track_index),
        client.get("/live/track/get/mute", track_index),
        client.get("/live/track/get/solo", track_index),
        client.get("/live/track/get/arm", track_index),
        client.get("/live/track/get/can_be_armed", track_index),
        client.get("/live/track/get/has_midi_input", track_index),
        client.get("/live/track/get/num_devices", track_index),
        client.get("/live/track/get/devices/name", track_index),
        client.get("/live/track/get/clips/name", track_index),
    )

    # Track-level list responses: (track_index, val1, val2, ...) — skip first element
    device_list = list(device_names[1:])
    clip_list = list(clip_names[1:])

    clips = [
        {"slot_index": i, "name": n}
        for i, n in enumerate(clip_list)
        if n is not None
    ]

    return {
        "index": track_index,
        "name": _scalar(name),
        "volume": _scalar(volume),
        "pan": _scalar(pan),
        "mute": bool(_scalar(mute)),
        "solo": bool(_scalar(solo)),
        "arm": bool(_scalar(arm)),
        "can_be_armed": bool(_scalar(can_be_armed)),
        "is_midi": bool(_scalar(is_midi)),
        "devices": device_list,
        "num_devices": _scalar(num_devices),
        "clips": clips,
    }


async def set_track_volume(
    client: "OscClient", track_index: int, volume: float
) -> dict[str, Any]:
    """Set track volume (0.0 = silent, 0.85 = unity gain, 1.0 = +6dB)."""
    if not (0.0 <= volume <= 1.0):
        raise ValueError(f"Volume must be 0.0–1.0, got {volume}")
    client.send("/live/track/set/volume", track_index, volume)
    return {"status": "ok", "track_index": track_index, "volume": volume}


async def set_track_pan(
    client: "OscClient", track_index: int, pan: float
) -> dict[str, Any]:
    """Set track panning (-1.0 = full left, 0.0 = centre, 1.0 = full right)."""
    if not (-1.0 <= pan <= 1.0):
        raise ValueError(f"Pan must be -1.0–1.0, got {pan}")
    client.send("/live/track/set/panning", track_index, pan)
    return {"status": "ok", "track_index": track_index, "pan": pan}


async def set_track_mute(
    client: "OscClient", track_index: int, mute: bool
) -> dict[str, Any]:
    """Mute or unmute a track."""
    client.send("/live/track/set/mute", track_index, int(mute))
    return {"status": "ok", "track_index": track_index, "mute": mute}


async def set_track_solo(
    client: "OscClient", track_index: int, solo: bool
) -> dict[str, Any]:
    """Solo or un-solo a track."""
    client.send("/live/track/set/solo", track_index, int(solo))
    return {"status": "ok", "track_index": track_index, "solo": solo}


async def set_track_arm(
    client: "OscClient", track_index: int, arm: bool
) -> dict[str, Any]:
    """Arm or disarm a track for recording."""
    client.send("/live/track/set/arm", track_index, int(arm))
    return {"status": "ok", "track_index": track_index, "arm": arm}


async def set_track_name(
    client: "OscClient", track_index: int, name: str
) -> dict[str, Any]:
    """Rename a track."""
    client.send("/live/track/set/name", track_index, name)
    return {"status": "ok", "track_index": track_index, "name": name}


async def get_track_send(
    client: "OscClient", track_index: int, send_index: int
) -> dict[str, Any]:
    """Get the current send level for a track return bus (0.0–1.0).

    Returns index 0 for the first return track (typically Reverb A),
    index 1 for the second (typically Delay B), etc.
    """
    result = await client.get("/live/track/get/send", track_index, send_index)
    return {"track_index": track_index, "send_index": send_index, "value": result[-1]}


async def set_track_send(
    client: "OscClient", track_index: int, send_index: int, value: float
) -> dict[str, Any]:
    """Set a send level for a track (0.0–1.0)."""
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"Send value must be 0.0–1.0, got {value}")
    client.send("/live/track/set/send", track_index, send_index, value)
    return {"status": "ok", "track_index": track_index, "send_index": send_index, "value": value}


async def get_available_input_routing_types(
    client: "OscClient", track_index: int
) -> dict[str, Any]:
    """List available input routing sources for an audio track.

    Returns track names, hardware inputs, and special sources like 'Resampling'.
    Only meaningful for audio tracks — MIDI tracks return MIDI sources.
    """
    result = await client.get(
        "/live/track/get/available_input_routing_types", track_index
    )
    # Response: (track_index, type1, type2, ...) — skip first element
    types = list(result[1:])
    return {"track_index": track_index, "types": types}


async def set_input_routing_type(
    client: "OscClient", track_index: int, routing_type: str
) -> dict[str, Any]:
    """Set the input routing source for a track.

    Use get_available_input_routing_types() to list valid values for this track.
    Common values: 'All Ins', 'No Input', or a track name like 'NB Top'.
    """
    client.send("/live/track/set/input_routing_type", track_index, routing_type)
    return {"status": "ok", "track_index": track_index, "input_routing_type": routing_type}


async def setup_resample_track(
    client: "OscClient", source_track_name: str
) -> dict[str, Any]:
    """Create an audio track pre-configured to capture another track's output.

    Creates a new audio track, routes its input to source_track_name, names it
    '{source_track_name} (Resampled)', and arms it for recording.

    After calling this, fire clip slot 0 on the returned track_index to start
    recording, then fire it again to commit the clip and stop.

    Args:
        source_track_name: The exact name of the source track (e.g. 'NB Top').
                           Must match a track name visible in Ableton.

    Returns:
        dict with track_index, name, input_routing, and next_step instructions.
    """
    # Create audio track
    result = await create_audio_track(client)
    new_idx = result["track_index"]

    name = f"{source_track_name} (Resampled)"
    client.send("/live/track/set/name", new_idx, name)
    client.send("/live/track/set/input_routing_type", new_idx, source_track_name)
    client.send("/live/track/set/arm", new_idx, 1)

    return {
        "status": "ready",
        "track_index": new_idx,
        "name": name,
        "input_routing": source_track_name,
        "next_step": (
            f"Track {new_idx} is armed. "
            "Call fire_clip(track_index, 0) to start recording into slot 0, "
            "then fire_clip(track_index, 0) again to stop and commit the clip."
        ),
    }


async def create_midi_track(client: "OscClient") -> dict[str, Any]:
    """Create a new MIDI track at the end of the session.

    Returns the index of the newly created track.
    """
    client.send("/live/song/create_midi_track")
    # AbletonOSC processes messages sequentially, so querying num_tracks
    # immediately after the create sees the updated count.
    num_after = (await client.get("/live/song/get/num_tracks"))[0]
    return {"status": "ok", "type": "midi", "track_index": num_after - 1}


async def create_audio_track(client: "OscClient") -> dict[str, Any]:
    """Create a new audio track at the end of the session.

    Returns the index of the newly created track.
    """
    client.send("/live/song/create_audio_track")
    num_after = (await client.get("/live/song/get/num_tracks"))[0]
    return {"status": "ok", "type": "audio", "track_index": num_after - 1}


async def create_return_track(client: "OscClient") -> dict[str, str]:
    """Create a new return track."""
    client.send("/live/song/create_return_track")
    return {"status": "ok", "type": "return"}


async def delete_track(client: "OscClient", track_index: int) -> dict[str, Any]:
    """Delete a track. This action cannot be undone via the MCP server."""
    client.send("/live/song/delete_track", track_index)
    return {"status": "ok", "deleted_track_index": track_index}


async def stop_track_clips(client: "OscClient", track_index: int) -> dict[str, Any]:
    """Stop all playing clips on a track."""
    client.send("/live/track/stop_all_clips", track_index)
    return {"status": "ok", "track_index": track_index}


async def duplicate_track(client: "OscClient", track_index: int) -> dict[str, Any]:
    """Duplicate a track."""
    client.send("/live/song/duplicate_track", track_index)
    return {"status": "ok", "duplicated_track_index": track_index}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar(args: tuple[Any, ...]) -> Any:
    """Extract the value from a track-level OSC response.

    AbletonOSC prefixes track-level responses with track_index:
        (track_index, value)
    The value is always the last element.
    """
    return args[-1] if args else None
