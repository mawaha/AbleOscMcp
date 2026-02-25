"""
Device parameter database tools: catalog, lookup, list, and set-by-name.
"""

from __future__ import annotations

from ableosc.client import OscClient
from ableosc.device_database import DeviceDatabase
from ableosc.tools import device as device_tools


async def catalog_device(
    client: OscClient,
    db: DeviceDatabase,
    track_index: int,
    device_index: int,
) -> dict:
    """
    Scan a device's parameters and store them in the local database.

    Call this once for each native Ableton instrument or effect you want
    Claude to be able to reference by parameter name.

    Args:
        track_index: Track index
        device_index: Device index on that track

    Returns:
        dict with device name and parameter count.
    """
    result = await device_tools.get_device_parameters(client, track_index, device_index)
    device_name = result["device_name"]
    parameters = result["parameters"]
    db.store(device_name, parameters)
    return {
        "device_name": device_name,
        "parameter_count": len(parameters),
        "status": "cataloged",
    }


async def list_known_devices(db: DeviceDatabase) -> dict:
    """
    List all devices currently in the local parameter database.

    Returns:
        dict with devices list (name, parameter_count, cataloged_at).
    """
    devices = db.list_devices()
    return {"devices": devices, "count": len(devices)}


async def lookup_parameter(
    db: DeviceDatabase,
    device_name: str,
    param_name: str,
) -> dict:
    """
    Search for a parameter by name within a catalogued device.

    Supports fuzzy matching: exact → starts-with → contains → word match.

    Args:
        device_name: Device name as it appears in Ableton (e.g. "Operator")
        param_name: Parameter name or partial name (e.g. "filter cutoff", "cutoff")

    Returns:
        dict with matches list, each containing index, name, min, max, value.
    """
    matches = db.lookup_parameter(device_name, param_name)
    return {
        "device_name": device_name,
        "query": param_name,
        "matches": matches,
        "count": len(matches),
    }


async def set_device_parameter_by_name(
    client: OscClient,
    db: DeviceDatabase,
    track_index: int,
    device_index: int,
    device_name: str,
    param_name: str,
    value: float,
) -> dict:
    """
    Look up a parameter by name and set it in one step.

    Requires that the device has been catalogued first with `catalog_device`.
    If the lookup returns multiple matches, the best match (first result) is used.

    Args:
        track_index: Track index
        device_index: Device index on that track
        device_name: Device name as catalogued (e.g. "Operator")
        param_name: Parameter name or partial name (e.g. "filter cutoff")
        value: Value to set (must be within the parameter's min/max range)

    Returns:
        dict with parameter name, index, value set, and match quality.
    """
    matches = db.lookup_parameter(device_name, param_name)
    if not matches:
        raise ValueError(
            f"No parameter matching {param_name!r} found in {device_name!r}. "
            "Try `lookup_parameter` to see available parameters."
        )

    best = matches[0]
    param_index = best["index"]

    await device_tools.set_device_parameter(client, track_index, device_index, param_index, value)
    return {
        "device_name": device_name,
        "param_name": best["name"],
        "param_index": param_index,
        "value": value,
        "match_quality": best["match_quality"],
    }
