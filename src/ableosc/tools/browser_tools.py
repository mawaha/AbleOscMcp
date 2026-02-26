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


def _device_type(name: str) -> str:
    """Infer device type from the browser item name/extension."""
    if name.endswith(".adg"):
        return "rack_preset"   # Ableton Device Group (Instrument/Effect Rack preset)
    if name.endswith(".adv"):
        return "preset"        # Native device preset (e.g. "Mellow Bass.adv")
    if name.endswith(".amxd"):
        return "max_device"    # Max for Live device
    return "device"            # Native device (e.g. "Analog", "Impulse")


async def list_browser_devices(client, category_name: str) -> dict[str, Any]:
    """Return loadable devices in a browser category with type hints.

    Each device is a dict with:
      name — display name (may include file extension for presets)
      type — one of: "device", "preset", "rack_preset", "max_device"
    """
    args = await client.get("/live/browser/get/devices", category_name)
    devices = [{"name": name, "type": _device_type(name)} for name in args]
    return {"category": category_name, "devices": devices}


async def list_presets(client, category_name: str, device_name: str) -> dict[str, Any]:
    """List the presets available for a specific device.

    Searches the named device's folder in the browser and returns all loadable
    preset names (.adv files, factory presets, etc.).

    category_name: e.g. "instruments", "audio_effects"
    device_name: e.g. "Analog", "Auto Filter"
    """
    args = await client.get("/live/browser/get/presets", category_name, device_name)
    return {"category": category_name, "device": device_name, "presets": list(args)}


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
