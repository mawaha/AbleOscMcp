"""Browser tools — search and load devices from the Ableton browser onto tracks.

These tools require the AbleOscRack Remote Script installed in Ableton Live.
They communicate on the rack_client (port 11002/11003).
"""

from __future__ import annotations

from typing import Any


async def list_browser_categories(client) -> dict[str, Any]:
    """Return the available browser category names."""
    args = await client.get("/live/browser/get/categories")
    return {"categories": list(args)}


async def list_browser_devices(client, category_name: str) -> dict[str, Any]:
    """Return the names of loadable devices in a browser category."""
    args = await client.get("/live/browser/get/devices", category_name)
    return {"category": category_name, "devices": list(args)}


async def load_device(
    client, track_index: int, category_name: str, device_name: str
) -> dict[str, Any]:
    """Search for a device by name and load it onto a track.

    Selects the target track as the hotswap target before loading, so the
    device lands on the correct track.

    Returns {"loaded": True, "name": <item_name>} on success, or
    {"loaded": False} if the device was not found in the given category.
    """
    args = await client.get(
        "/live/browser/load", track_index, category_name, device_name
    )
    if args and args[0] == 1:
        return {"loaded": True, "name": str(args[1]) if len(args) > 1 else device_name}
    return {"loaded": False}
