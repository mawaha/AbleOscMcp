"""Rack chain traversal tools.

Requires AbleOscRack Remote Script installed in Ableton Live (separate from
AbletonOSC), listening on port 11002 / replying on port 11003.

OSC address conventions:
  /live/rack/get/...                  (track_idx, device_idx, ...)
  /live/rack/get/chain/...            (track_idx, device_idx, chain_idx, ...)
  /live/rack/get/chain/device/...     (track_idx, device_idx, chain_idx, dev_idx, ...)
  /live/rack/set/chain/device/...     (... + param_idx + value)

Response prefix convention (matches AbletonOSC):
  rack-level scalars:          (track_idx, device_idx, value)           → args[-1]
  rack-level lists:            (track_idx, device_idx, v0, v1, ...)     → args[2:]
  chain-level scalars:         (track_idx, device_idx, chain_idx, v)    → args[-1]
  chain-level lists:           (..., v0, v1, ...)                       → args[3:]
  chain-device scalars:        (... , dev_idx, v)                       → args[-1]
  chain-device lists:          (..., dev_idx, v0, v1, ...)              → args[4:]
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ableosc.client import OscClient


async def get_rack_chains(
    client: "OscClient", track_index: int, device_index: int
) -> dict[str, Any]:
    """List all chains in a rack device."""
    num_result, names_result = await asyncio.gather(
        client.get("/live/rack/get/num_chains", track_index, device_index),
        client.get("/live/rack/get/chains/name", track_index, device_index),
    )
    count = _scalar(num_result)
    names = list(names_result[2:])
    chains = [{"index": i, "name": names[i] if i < len(names) else "?"} for i in range(count)]
    return {
        "track_index": track_index,
        "device_index": device_index,
        "chains": chains,
        "count": count,
    }


async def get_chain_devices(
    client: "OscClient", track_index: int, device_index: int, chain_index: int
) -> dict[str, Any]:
    """List all devices in a rack chain."""
    (
        num_result,
        names_result,
        class_names_result,
        can_chain_result,
    ) = await asyncio.gather(
        client.get("/live/rack/get/chain/num_devices", track_index, device_index, chain_index),
        client.get("/live/rack/get/chain/devices/name", track_index, device_index, chain_index),
        client.get("/live/rack/get/chain/devices/class_name", track_index, device_index, chain_index),
        client.get("/live/rack/get/chain/devices/can_have_chains", track_index, device_index, chain_index),
    )
    count = _scalar(num_result)
    names = list(names_result[3:])
    class_names = list(class_names_result[3:])
    can_chain = list(can_chain_result[3:])
    devices = [
        {
            "index": i,
            "name": names[i] if i < len(names) else "?",
            "class_name": class_names[i] if i < len(class_names) else "?",
            "can_have_chains": bool(can_chain[i]) if i < len(can_chain) else False,
        }
        for i in range(count)
    ]
    return {
        "track_index": track_index,
        "device_index": device_index,
        "chain_index": chain_index,
        "devices": devices,
        "count": count,
    }


async def get_chain_device_parameters(
    client: "OscClient",
    track_index: int,
    device_index: int,
    chain_index: int,
    nested_device_index: int,
) -> dict[str, Any]:
    """Get all parameters for a device inside a rack chain."""
    (
        name_result,
        num_params,
        param_names,
        param_values,
        param_mins,
        param_maxs,
        param_quantized,
    ) = await asyncio.gather(
        client.get("/live/rack/get/chain/device/name",
                   track_index, device_index, chain_index, nested_device_index),
        client.get("/live/rack/get/chain/device/num_parameters",
                   track_index, device_index, chain_index, nested_device_index),
        client.get("/live/rack/get/chain/device/parameters/name",
                   track_index, device_index, chain_index, nested_device_index),
        client.get("/live/rack/get/chain/device/parameters/value",
                   track_index, device_index, chain_index, nested_device_index),
        client.get("/live/rack/get/chain/device/parameters/min",
                   track_index, device_index, chain_index, nested_device_index),
        client.get("/live/rack/get/chain/device/parameters/max",
                   track_index, device_index, chain_index, nested_device_index),
        client.get("/live/rack/get/chain/device/parameters/is_quantized",
                   track_index, device_index, chain_index, nested_device_index),
    )
    count = _scalar(num_params)
    # Responses: (track_idx, device_idx, chain_idx, nested_dev_idx, val0, val1, ...) — skip first 4
    names_list = param_names[4:]
    values_list = param_values[4:]
    mins_list = param_mins[4:]
    maxs_list = param_maxs[4:]
    quantized_list = param_quantized[4:]
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
        "chain_index": chain_index,
        "nested_device_index": nested_device_index,
        "device_name": _scalar(name_result),
        "parameters": params,
        "count": count,
    }


async def set_chain_device_parameter(
    client: "OscClient",
    track_index: int,
    device_index: int,
    chain_index: int,
    nested_device_index: int,
    param_index: int,
    value: float,
) -> dict[str, Any]:
    """Set a parameter on a device inside a rack chain."""
    client.send(
        "/live/rack/set/chain/device/parameter/value",
        track_index,
        device_index,
        chain_index,
        nested_device_index,
        param_index,
        value,
    )
    return {
        "status": "ok",
        "track_index": track_index,
        "device_index": device_index,
        "chain_index": chain_index,
        "nested_device_index": nested_device_index,
        "param_index": param_index,
        "value": value,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar(args: tuple[Any, ...]) -> Any:
    """Extract the scalar value from a prefixed OSC response.

    All rack responses are prefixed with index coords. The value is always last.
    """
    return args[-1] if args else None
