"""Subscription registry for real-time AbletonOSC listener management.

AbletonOSC listeners push property changes on the GET address whenever a value
changes. This module bridges that push model to MCP's poll-based request/response
pattern using asyncio.Queue.

Index-prefix rules for listener response args (differs from GET for device level):
    song/view:   (value,)                         → num_index_args = 0
    track:       (track_index, value)             → num_index_args = 1
    scene:       (scene_index, value)             → num_index_args = 1
    clip/slot:   (track_index, clip_index, value) → num_index_args = 2
    device:      (value,)                         → num_index_args = 0
                 (device handler passes empty params to _start_listen)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ableosc.client import OscClient


@dataclass
class Subscription:
    sub_id: str
    stop_address: str
    listen_args: tuple[Any, ...]
    response_address: str
    num_index_args: int
    queue: asyncio.Queue  # type: ignore[type-arg]
    callback: Callable[..., None]


class SubscriptionRegistry:
    """Thread-safe registry of active AbletonOSC property subscriptions."""

    def __init__(self) -> None:
        self._subs: dict[str, Subscription] = {}

    def create(
        self,
        client: "OscClient",
        listen_address: str,
        stop_address: str,
        listen_args: tuple[Any, ...],
        response_address: str,
        num_index_args: int,
    ) -> Subscription:
        """Register a new listener and return the subscription."""
        sub_id = "sub_" + uuid.uuid4().hex[:8]
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def callback(address: str, *args: Any) -> None:
            value_args = args[num_index_args:]
            value = value_args[0] if len(value_args) == 1 else value_args
            queue.put_nowait({"value": value})

        client.add_listener(response_address, callback)
        client.send(listen_address, *listen_args)

        sub = Subscription(
            sub_id=sub_id,
            stop_address=stop_address,
            listen_args=listen_args,
            response_address=response_address,
            num_index_args=num_index_args,
            queue=queue,
            callback=callback,
        )
        self._subs[sub_id] = sub
        return sub

    def get(self, sub_id: str) -> Subscription | None:
        return self._subs.get(sub_id)

    def remove(self, sub_id: str, client: "OscClient") -> bool:
        """Unregister listener and send stop_listen. Returns False if sub_id unknown."""
        sub = self._subs.pop(sub_id, None)
        if sub is None:
            return False
        client.remove_listener(sub.response_address, sub.callback)
        client.send(sub.stop_address, *sub.listen_args)
        return True

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "sub_id": s.sub_id,
                "response_address": s.response_address,
                "queued_events": s.queue.qsize(),
            }
            for s in self._subs.values()
        ]


# ---------------------------------------------------------------------------
# Address builder
# ---------------------------------------------------------------------------

_VALID_LEVELS = {"song", "track", "clip", "clip_slot", "scene", "device", "view"}


def build_addresses(
    level: str,
    prop: str,
    track_index: int | None = None,
    clip_index: int | None = None,
    scene_index: int | None = None,
    device_index: int | None = None,
) -> tuple[str, str, str, tuple[Any, ...], int]:
    """Compute the three OSC addresses and metadata for a subscription.

    Returns:
        (start_listen_addr, stop_listen_addr, get_addr, listen_args, num_index_args)
    """
    if level not in _VALID_LEVELS:
        raise ValueError(
            f"Unknown level {level!r}. Valid levels: {sorted(_VALID_LEVELS)}"
        )

    base = f"/live/{level}"
    start = f"{base}/start_listen/{prop}"
    stop = f"{base}/stop_listen/{prop}"
    get = f"{base}/get/{prop}"

    if level in ("song", "view"):
        return start, stop, get, (), 0

    if level == "track":
        _require(track_index, "track_index", level)
        return start, stop, get, (track_index,), 1

    if level == "scene":
        _require(scene_index, "scene_index", level)
        return start, stop, get, (scene_index,), 1

    if level in ("clip", "clip_slot"):
        _require(track_index, "track_index", level)
        _require(clip_index, "clip_index", level)
        return start, stop, get, (track_index, clip_index), 2

    if level == "device":
        _require(track_index, "track_index", level)
        _require(device_index, "device_index", level)
        # AbletonOSC device handler passes empty params to _start_listen, so
        # listener responses arrive as (value,) with no index prefix.
        return start, stop, get, (track_index, device_index), 0

    raise ValueError(f"Unhandled level: {level!r}")  # unreachable


def _require(value: Any, name: str, level: str) -> None:
    if value is None:
        raise ValueError(f"{name!r} is required for level {level!r}")
