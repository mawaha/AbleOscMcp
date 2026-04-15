"""Live co-pilot: watches Ableton events and returns rich observations for analysis."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient
    from ableosc.subscriptions import SubscriptionRegistry

from ableosc.tools import listen as listen_tools
from ableosc.tools import song as song_tools
from ableosc.tools import track as track_tools


async def run_copilot(
    client: "OscClient",
    registry: "SubscriptionRegistry",
    duration_seconds: int = 120,
) -> dict[str, Any]:
    """Watch for Ableton events and collect rich observations for each.

    Subscribes to track selection and tempo changes. On each event, fetches
    full track details and records them. Returns the full session context and
    ordered event log so the caller can generate suggestions.

    Returns:
        {
            "session": { tempo, num_tracks, tracks[] },
            "events": [ { "type", "label", "track_data" | "tempo" } ]
        }
    """
    # Snapshot session context once
    session_info = await song_tools.get_session_info(client)
    tracks_info = await track_tools.get_tracks(client)
    session_context = {
        "tempo": session_info.get("tempo"),
        "num_tracks": tracks_info.get("count"),
        "tracks": [
            {
                "index": t["index"],
                "name": t["name"],
                "is_midi": t["is_midi"],
                "volume": t.get("volume"),
                "mute": t.get("mute"),
            }
            for t in tracks_info.get("tracks", [])
        ],
    }

    # Subscribe to selected_track and tempo
    track_sub = await listen_tools.subscribe(client, registry, "selected_track", "view")
    tempo_sub = await listen_tools.subscribe(client, registry, "tempo", "song")
    track_sub_id = track_sub["sub_id"]
    tempo_sub_id = tempo_sub["sub_id"]

    last_track_index: int | None = None
    last_tempo: float | None = None
    last_event_time: float = 0.0
    events: list[dict[str, Any]] = []
    start_time = time.monotonic()

    try:
        while time.monotonic() - start_time < duration_seconds:
            # Poll track selection — blocks up to 2s
            track_result = await listen_tools.poll(
                registry, track_sub_id, timeout_seconds=2.0
            )
            # Non-blocking drain of tempo events
            tempo_result = await listen_tools.poll(
                registry, tempo_sub_id, timeout_seconds=0.05
            )

            now = time.monotonic()

            # Track selection — debounce at 1.5s
            track_events = track_result.get("events", [])
            if track_events:
                track_index = track_events[-1].get("value")
                if (
                    track_index is not None
                    and track_index != last_track_index
                    and (now - last_event_time) > 1.5
                ):
                    last_track_index = track_index
                    last_event_time = now
                    try:
                        track_data = await track_tools.get_track(client, track_index)
                        events.append({
                            "type": "track_selected",
                            "label": f"Track {track_index}: \"{track_data['name']}\"",
                            "track_data": track_data,
                        })
                    except Exception:
                        pass

            # Tempo change
            tempo_events = tempo_result.get("events", [])
            if tempo_events:
                new_tempo = tempo_events[-1].get("value")
                if new_tempo is not None and new_tempo != last_tempo:
                    last_tempo = new_tempo
                    events.append({
                        "type": "tempo_changed",
                        "label": f"Tempo → {new_tempo:.1f} BPM",
                        "tempo": new_tempo,
                    })

    finally:
        await listen_tools.unsubscribe(client, registry, track_sub_id)
        await listen_tools.unsubscribe(client, registry, tempo_sub_id)

    return {"session": session_context, "events": events}
