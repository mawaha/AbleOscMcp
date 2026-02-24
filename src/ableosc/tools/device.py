"""Device tools: inspect and control parameters on Ableton devices (instruments, effects)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient

_DEVICE_TYPES = {0: "audio_effect", 1: "instrument", 2: "midi_effect"}


async def get_devices(client: "OscClient", track_index: int) -> dict[str, Any]:
    """List all devices on a track with their names and types."""
    num_result, names, types, class_names = await asyncio.gather(
        client.get("/live/track/get/num_devices", track_index),
        client.get("/live/track/get/devices/name", track_index),
        client.get("/live/track/get/devices/type", track_index),
        client.get("/live/track/get/devices/class_name", track_index),
    )
    count = _scalar(num_result)
    # Track-level list responses: (track_index, val1, val2, ...) — skip first element
    name_list = names[1:]
    type_list = types[1:]
    class_list = class_names[1:]
    devices = [
        {
            "index": i,
            "name": name_list[i] if i < len(name_list) else "?",
            "type": _DEVICE_TYPES.get(type_list[i] if i < len(type_list) else -1, "unknown"),
            "class_name": class_list[i] if i < len(class_list) else "?",
        }
        for i in range(count)
    ]
    return {"track_index": track_index, "devices": devices, "count": count}


async def get_device_parameters(
    client: "OscClient", track_index: int, device_index: int
) -> dict[str, Any]:
    """Get all parameters for a device, including names, values, and ranges."""
    (
        name_result,
        num_params,
        param_names,
        param_values,
        param_mins,
        param_maxs,
        param_quantized,
    ) = await asyncio.gather(
        client.get("/live/device/get/name", track_index, device_index),
        client.get("/live/device/get/num_parameters", track_index, device_index),
        client.get("/live/device/get/parameters/name", track_index, device_index),
        client.get("/live/device/get/parameters/value", track_index, device_index),
        client.get("/live/device/get/parameters/min", track_index, device_index),
        client.get("/live/device/get/parameters/max", track_index, device_index),
        client.get("/live/device/get/parameters/is_quantized", track_index, device_index),
    )

    count = _scalar(num_params)
    # Device-level list responses: (track_index, device_index, val1, val2, ...) — skip first two
    names_list = param_names[2:]
    values_list = param_values[2:]
    mins_list = param_mins[2:]
    maxs_list = param_maxs[2:]
    quantized_list = param_quantized[2:]
    params = [
        {
            "index": i,
            "name": names_list[i] if i < len(names_list) else "?",
            "value": values_list[i] if i < len(values_list) else None,
            "min": mins_list[i] if i < len(mins_list) else None,
            "max": maxs_list[i] if i < len(maxs_list) else None,
            "is_quantized": bool(quantized_list[i]) if i < len(quantized_list) else False,
        }
        for i in range(count)
    ]
    return {
        "track_index": track_index,
        "device_index": device_index,
        "device_name": _scalar(name_result),
        "parameters": params,
        "count": count,
    }


async def get_device_parameter(
    client: "OscClient",
    track_index: int,
    device_index: int,
    param_index: int,
) -> dict[str, Any]:
    """Get the current value and display string for a single device parameter."""
    value_result, string_result = await asyncio.gather(
        client.get("/live/device/get/parameter/value", track_index, device_index, param_index),
        client.get(
            "/live/device/get/parameter/value_string", track_index, device_index, param_index
        ),
    )
    value = _scalar(value_result)
    display = _scalar(string_result)
    return {
        "track_index": track_index,
        "device_index": device_index,
        "param_index": param_index,
        "value": value,
        "display": display,
    }


async def set_device_parameter(
    client: "OscClient",
    track_index: int,
    device_index: int,
    param_index: int,
    value: float,
) -> dict[str, Any]:
    """Set a device parameter to a new value.

    Value should be within the parameter's min/max range. Use get_device_parameters
    to discover the valid range for each parameter.
    """
    client.send(
        "/live/device/set/parameter/value",
        track_index,
        device_index,
        param_index,
        value,
    )
    return {
        "status": "ok",
        "track_index": track_index,
        "device_index": device_index,
        "param_index": param_index,
        "value": value,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar(args: tuple[Any, ...]) -> Any:
    """Extract the value from a device-level OSC response.

    AbletonOSC prefixes device-level responses with track_index and device_index
    (and sometimes param_index). The value is always the last element.
    """
    return args[-1] if args else None
