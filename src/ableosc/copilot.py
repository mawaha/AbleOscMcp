"""Live co-pilot: watches Ableton events and feeds them to Claude for suggestions."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient
    from ableosc.subscriptions import SubscriptionRegistry

from ableosc.tools import listen as listen_tools
from ableosc.tools import song as song_tools
from ableosc.tools import track as track_tools


_SYSTEM_PROMPT = """\
You are an expert music producer and Ableton Live co-pilot watching a live session in real time.

When the user navigates to a track or changes the tempo, respond with a brief observation \
and 1-2 specific, actionable suggestions — creative or technical. You have the full session \
context and a rolling conversation history, so your suggestions should build on what you've \
already seen the user doing.

Keep responses to 3-5 sentences. Be direct and musical. Reference actual device names, \
parameter values, and track names from the context you're given. Think like a collaborator \
sitting next to the producer.\
"""


async def run_copilot(
    client: "OscClient",
    registry: "SubscriptionRegistry",
    duration_seconds: int = 120,
) -> list[dict[str, Any]]:
    """Watch for Ableton events and generate Claude suggestions for each.

    Subscribes to track selection and tempo changes. On each event, fetches
    full track details and calls Claude for contextual suggestions.

    Returns a log of all (event, suggestion) pairs from the session.
    """
    from anthropic import Anthropic

    claude = Anthropic()
    log: list[dict[str, Any]] = []

    # Snapshot session context once — used as background for every Claude call
    session_info = await song_tools.get_session_info(client)
    tracks_info = await track_tools.get_tracks(client)
    session_context = {
        "tempo": session_info.get("tempo"),
        "num_tracks": tracks_info.get("count"),
        "tracks": [
            {"index": t["index"], "name": t["name"], "is_midi": t["is_midi"]}
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
    conversation: list[dict[str, str]] = []
    start_time = time.monotonic()

    try:
        while time.monotonic() - start_time < duration_seconds:
            # Poll track selection — blocks up to 2s waiting for an event
            track_result = await listen_tools.poll(
                registry, track_sub_id, timeout_seconds=2.0
            )
            # Non-blocking drain of any pending tempo events
            tempo_result = await listen_tools.poll(
                registry, tempo_sub_id, timeout_seconds=0.05
            )

            now = time.monotonic()
            event_data: dict[str, Any] | None = None

            # Track selection — take the most recent event, debounce at 1.5s
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
                        event_data = {
                            "type": "track_selected",
                            "track_index": track_index,
                            "track_data": track_data,
                        }
                    except Exception:
                        pass

            # Tempo change — only processed if no track event this cycle
            if not event_data:
                tempo_events = tempo_result.get("events", [])
                if tempo_events:
                    new_tempo = tempo_events[-1].get("value")
                    if new_tempo is not None and new_tempo != last_tempo:
                        last_tempo = new_tempo
                        event_data = {"type": "tempo_changed", "tempo": new_tempo}

            if not event_data:
                continue

            # Build the user message for Claude
            if event_data["type"] == "track_selected":
                td = event_data["track_data"]
                user_msg = (
                    f"Session: {json.dumps(session_context)}\n\n"
                    f"User selected Track {event_data['track_index']}: \"{td['name']}\"\n"
                    f"Type: {'MIDI' if td.get('is_midi') else 'Audio'}\n"
                    f"Devices: {td.get('devices', [])}\n"
                    f"Volume: {td.get('volume', 0):.2f}  "
                    f"Pan: {td.get('pan', 0):.2f}  "
                    f"Mute: {td.get('mute')}  "
                    f"Solo: {td.get('solo')}\n"
                    f"Clips: {len(td.get('clips', []))}"
                )
                label = f"Track {event_data['track_index']}: \"{td['name']}\""
            else:
                user_msg = (
                    f"Session: {json.dumps(session_context)}\n\n"
                    f"User changed tempo to {event_data['tempo']:.1f} BPM"
                )
                label = f"Tempo → {event_data['tempo']:.1f} BPM"

            # Call Claude — rolling conversation history keeps context across events
            messages = conversation[-8:] + [{"role": "user", "content": user_msg}]
            try:
                response = claude.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    system=_SYSTEM_PROMPT,
                    messages=messages,
                )
                suggestion = response.content[0].text
                conversation.append({"role": "user", "content": user_msg})
                conversation.append({"role": "assistant", "content": suggestion})
            except Exception as e:
                suggestion = f"(Claude API error: {e})"

            log.append({"event": label, "suggestion": suggestion})

    finally:
        await listen_tools.unsubscribe(client, registry, track_sub_id)
        await listen_tools.unsubscribe(client, registry, tempo_sub_id)

    return log
