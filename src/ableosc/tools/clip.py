"""Clip-level tools: creation, MIDI notes, playback, loop settings."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient

# A MIDI note dict has these keys:
# pitch       int  0-127 (60 = middle C)
# start_time  float beats from clip start
# duration    float beats
# velocity    int  0-127
# mute        int  0 or 1 (0 = audible)
NoteDict = dict[str, Any]

_NOTE_FIELDS = ("pitch", "start_time", "duration", "velocity", "mute")


async def get_clip_info(
    client: "OscClient", track_index: int, clip_index: int
) -> dict[str, Any]:
    """Get metadata for a clip."""
    (
        name,
        length,
        looping,
        loop_start,
        loop_end,
        is_playing,
        color,
    ) = await asyncio.gather(
        client.get("/live/clip/get/name", track_index, clip_index),
        client.get("/live/clip/get/length", track_index, clip_index),
        client.get("/live/clip/get/looping", track_index, clip_index),
        client.get("/live/clip/get/loop_start", track_index, clip_index),
        client.get("/live/clip/get/loop_end", track_index, clip_index),
        client.get("/live/clip/get/is_playing", track_index, clip_index),
        client.get("/live/clip/get/color", track_index, clip_index),
    )
    return {
        "track_index": track_index,
        "clip_index": clip_index,
        "name": _scalar(name),
        "length_beats": _scalar(length),
        "looping": bool(_scalar(looping)),
        "loop_start_beats": _scalar(loop_start),
        "loop_end_beats": _scalar(loop_end),
        "is_playing": bool(_scalar(is_playing)),
        "color": _scalar(color),
    }


async def create_clip(
    client: "OscClient",
    track_index: int,
    clip_index: int,
    length_beats: float = 4.0,
) -> dict[str, Any]:
    """Create a new empty MIDI clip in a clip slot."""
    if length_beats <= 0:
        raise ValueError(f"Clip length must be positive, got {length_beats}")
    client.send("/live/clip_slot/create_clip", track_index, clip_index, length_beats)
    return {
        "status": "ok",
        "track_index": track_index,
        "clip_index": clip_index,
        "length_beats": length_beats,
    }


async def delete_clip(
    client: "OscClient", track_index: int, clip_index: int
) -> dict[str, Any]:
    """Delete a clip from a slot."""
    client.send("/live/clip_slot/delete_clip", track_index, clip_index)
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index}


async def fire_clip(
    client: "OscClient", track_index: int, clip_index: int
) -> dict[str, Any]:
    """Fire (launch) a clip slot."""
    client.send("/live/clip_slot/fire", track_index, clip_index)
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index}


async def stop_clip(
    client: "OscClient", track_index: int, clip_index: int
) -> dict[str, Any]:
    """Stop a clip slot."""
    client.send("/live/clip_slot/stop", track_index, clip_index)
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index}


async def set_clip_name(
    client: "OscClient", track_index: int, clip_index: int, name: str
) -> dict[str, Any]:
    """Rename a clip."""
    client.send("/live/clip/set/name", track_index, clip_index, name)
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index, "name": name}


async def set_clip_loop(
    client: "OscClient",
    track_index: int,
    clip_index: int,
    looping: bool,
    loop_start: float | None = None,
    loop_end: float | None = None,
) -> dict[str, Any]:
    """Configure loop settings for a clip."""
    client.send("/live/clip/set/looping", track_index, clip_index, int(looping))
    if loop_start is not None:
        client.send("/live/clip/set/loop_start", track_index, clip_index, loop_start)
    if loop_end is not None:
        client.send("/live/clip/set/loop_end", track_index, clip_index, loop_end)
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index}


async def get_notes(
    client: "OscClient",
    track_index: int,
    clip_index: int,
) -> dict[str, Any]:
    """Get all MIDI notes from a clip.

    Returns notes as a list of dicts with keys:
        pitch, start_time, duration, velocity, mute
    """
    result = await client.get("/live/clip/get/notes", track_index, clip_index)
    notes = _parse_notes(result)
    return {
        "track_index": track_index,
        "clip_index": clip_index,
        "notes": notes,
        "count": len(notes),
    }


async def add_notes(
    client: "OscClient",
    track_index: int,
    clip_index: int,
    notes: list[NoteDict],
) -> dict[str, Any]:
    """Add MIDI notes to a clip.

    Each note must have: pitch (0-127), start_time (beats), duration (beats),
    velocity (0-127), mute (0 or 1).

    Notes are APPENDED to any existing notes — existing notes are not removed.
    """
    if not notes:
        raise ValueError("notes list must not be empty")
    flat_args = _flatten_notes(notes)
    client.send("/live/clip/add/notes", track_index, clip_index, *flat_args)
    return {
        "status": "ok",
        "track_index": track_index,
        "clip_index": clip_index,
        "added_count": len(notes),
    }


async def remove_notes(
    client: "OscClient",
    track_index: int,
    clip_index: int,
    pitch_start: int | None = None,
    pitch_span: int | None = None,
    time_start: float | None = None,
    time_span: float | None = None,
) -> dict[str, Any]:
    """Remove MIDI notes from a clip.

    Without arguments, removes all notes. With arguments, removes notes within
    the given pitch and time ranges:
      pitch_start/span: semitone range (0-127)
      time_start/span:  beat range from clip start
    """
    if all(v is None for v in (pitch_start, pitch_span, time_start, time_span)):
        client.send("/live/clip/remove/notes", track_index, clip_index)
    else:
        p_start = pitch_start if pitch_start is not None else 0
        p_span = pitch_span if pitch_span is not None else 128
        t_start = time_start if time_start is not None else 0.0
        t_span = time_span if time_span is not None else 1_000_000.0
        client.send(
            "/live/clip/remove/notes",
            track_index,
            clip_index,
            p_start,
            p_span,
            t_start,
            t_span,
        )
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index}


async def duplicate_clip_loop(
    client: "OscClient", track_index: int, clip_index: int
) -> dict[str, Any]:
    """Double the loop length of a clip by duplicating its content."""
    client.send("/live/clip/duplicate_loop", track_index, clip_index)
    return {"status": "ok", "track_index": track_index, "clip_index": clip_index}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar(args: tuple[Any, ...]) -> Any:
    """Extract the first value from an OSC response tuple."""
    return args[0] if args else None


def _parse_notes(args: tuple[Any, ...]) -> list[NoteDict]:
    """Parse a flat OSC note sequence into a list of note dicts.

    AbletonOSC encodes notes as a flat sequence:
        pitch start_time duration velocity mute  [repeated]
    """
    notes: list[NoteDict] = []
    flat = list(args)
    for i in range(0, len(flat) - 4, 5):
        notes.append(
            {
                "pitch": int(flat[i]),
                "start_time": float(flat[i + 1]),
                "duration": float(flat[i + 2]),
                "velocity": int(flat[i + 3]),
                "mute": int(flat[i + 4]),
            }
        )
    return notes


def _flatten_notes(notes: list[NoteDict]) -> list[Any]:
    """Flatten note dicts into the sequence expected by AbletonOSC add/notes."""
    flat: list[Any] = []
    for note in notes:
        flat.extend(
            [
                int(note.get("pitch", 60)),
                float(note.get("start_time", 0.0)),
                float(note.get("duration", 0.25)),
                int(note.get("velocity", 100)),
                int(note.get("mute", 0)),
            ]
        )
    return flat
