"""Real-time listener tools: subscribe, poll, unsubscribe.

Usage pattern:
    1. Call subscribe() → returns sub_id immediately.
       AbletonOSC sends the current value right away, so poll() will have
       at least one event queued before you even ask.
    2. Call poll(sub_id) to collect events. Blocks up to timeout_seconds
       if the queue is empty (waits for the next change).
    3. Call unsubscribe(sub_id) when done.

Example properties by level:
    song:       tempo, is_playing, loop, session_record, groove_amount
    track:      mute, solo, arm, volume, panning, output_meter_level
    clip:       is_playing, is_recording, playing_position, name
    clip_slot:  has_clip, is_playing, is_triggered
    scene:      name
    device:     name
    view:       selected_scene, selected_track
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient
    from ableosc.subscriptions import SubscriptionRegistry


async def subscribe(
    client: "OscClient",
    registry: "SubscriptionRegistry",
    prop: str,
    level: str = "song",
    track_index: int | None = None,
    clip_index: int | None = None,
    scene_index: int | None = None,
    device_index: int | None = None,
) -> dict[str, Any]:
    """Start a persistent listener for a Live property.

    Returns a sub_id immediately. AbletonOSC pushes the current value on
    subscribe, so poll() will have at least one event right away.
    """
    from ableosc.subscriptions import build_addresses

    start_addr, stop_addr, get_addr, listen_args, num_index_args = build_addresses(
        level, prop, track_index, clip_index, scene_index, device_index
    )
    sub = registry.create(
        client=client,
        listen_address=start_addr,
        stop_address=stop_addr,
        listen_args=listen_args,
        response_address=get_addr,
        num_index_args=num_index_args,
    )
    return {
        "sub_id": sub.sub_id,
        "response_address": get_addr,
        "status": "subscribed",
    }


async def poll(
    registry: "SubscriptionRegistry",
    sub_id: str,
    timeout_seconds: float = 5.0,
    max_events: int = 20,
) -> dict[str, Any]:
    """Return queued events for a subscription.

    Drains whatever has accumulated since the last poll. If the queue is empty,
    blocks up to timeout_seconds waiting for the next event. Returns an empty
    events list (not an error) if nothing arrives within the timeout.
    """
    sub = registry.get(sub_id)
    if sub is None:
        raise ValueError(f"Unknown subscription: {sub_id!r}")

    events: list[dict[str, Any]] = []

    # Drain already-queued events first
    while not sub.queue.empty() and len(events) < max_events:
        events.append(sub.queue.get_nowait())

    # If nothing was queued, block until the first event or timeout
    if not events and timeout_seconds > 0:
        try:
            async with asyncio.timeout(timeout_seconds):
                event = await sub.queue.get()
            events.append(event)
            # Drain any further events that arrived during the wait
            while not sub.queue.empty() and len(events) < max_events:
                events.append(sub.queue.get_nowait())
        except TimeoutError:
            pass

    return {
        "sub_id": sub_id,
        "events": events,
        "queued_remaining": sub.queue.qsize(),
    }


async def unsubscribe(
    client: "OscClient",
    registry: "SubscriptionRegistry",
    sub_id: str,
) -> dict[str, Any]:
    """Stop a listener and remove the subscription."""
    if not registry.remove(sub_id, client):
        raise ValueError(f"Unknown subscription: {sub_id!r}")
    return {"sub_id": sub_id, "status": "unsubscribed"}


async def list_subscriptions(
    registry: "SubscriptionRegistry",
) -> dict[str, Any]:
    """List all active subscriptions and their queued event counts."""
    return {"subscriptions": registry.list_all()}
