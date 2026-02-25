"""
Device parameter database tools: catalog, lookup, list, set-by-name, and annotation.
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


async def annotate_parameter(
    db: DeviceDatabase,
    device_name: str,
    param_name: str,
    info_title: str,
    info_text: str,
) -> dict:
    """
    Add or update the Info View title and description for a parameter.

    Use this to manually store the text shown in Ableton's Info View panel,
    which provides human-readable descriptions of what each parameter does.

    Args:
        device_name: Device name as catalogued (e.g. "Operator")
        param_name: Parameter name to annotate (exact or partial match)
        info_title: Info View title e.g. "Filter Frequency"
        info_text: Info View description e.g. "This defines the center or cutoff frequency..."

    Returns:
        dict with the annotated parameter details.
    """
    matches = db.lookup_parameter(device_name, param_name)
    if not matches:
        raise ValueError(
            f"No parameter matching {param_name!r} found in {device_name!r}."
        )
    best = matches[0]
    success = db.annotate_parameter(device_name, best["index"], info_title, info_text)
    return {
        "device_name": device_name,
        "param_name": best["name"],
        "param_index": best["index"],
        "info_title": info_title,
        "info_text": info_text,
        "saved": success,
    }


async def read_info_view() -> dict:
    """
    Read the current Info View title and text from Ableton Live's UI.

    Uses the macOS Accessibility API to capture whatever text Ableton is
    currently showing in the Info View panel. Hover over any control in
    Ableton before calling this, then immediately call this tool.

    Requires:
        - macOS only
        - Terminal (or the server process) must have Accessibility access:
          System Settings → Privacy & Security → Accessibility

    Returns:
        dict with title and text fields, or a status message if unavailable.
    """
    from ableosc import info_view
    if not info_view.is_available():
        return {
            "status": "unavailable",
            "reason": "macOS Accessibility API not available. Install pyobjc or check platform.",
        }
    try:
        result = info_view.read_info_view()
        if result is None:
            return {"status": "not_found", "reason": "Could not locate Info View in Ableton's UI"}
        return {"status": "ok", "title": result["title"], "text": result["text"]}
    except ImportError as e:
        return {"status": "unavailable", "reason": str(e)}
    except RuntimeError as e:
        return {"status": "error", "reason": str(e)}


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
