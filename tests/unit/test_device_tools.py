"""Unit tests for device tools."""

from __future__ import annotations

import pytest

from ableosc.tools import device as device_tools
from tests.conftest import MockOscClient

pytestmark = pytest.mark.unit


def _setup_devices(mock: MockOscClient, track_index: int = 0) -> None:
    """Responses do NOT include track_index prefix."""
    mock.when_get("/live/track/get/num_devices", 2)
    mock.when_get("/live/track/get/devices/name", "Operator", "Auto Filter")
    mock.when_get("/live/track/get/devices/type", 1, 0)  # instrument, audio_effect
    mock.when_get("/live/track/get/devices/class_name", "Operator", "AutoFilter")


def _setup_device_params(mock: MockOscClient, track: int = 0, device: int = 0) -> None:
    """Responses do NOT include track/device index prefix."""
    mock.when_get("/live/device/get/name", "Operator")
    mock.when_get("/live/device/get/num_parameters", 3)
    mock.when_get(
        "/live/device/get/parameters/name",
        "Device On", "Osc A Waveform", "Filter Freq"
    )
    mock.when_get(
        "/live/device/get/parameters/value",
        1.0, 0.0, 0.5
    )
    mock.when_get(
        "/live/device/get/parameters/min",
        0.0, 0.0, 0.0
    )
    mock.when_get(
        "/live/device/get/parameters/max",
        1.0, 4.0, 1.0
    )
    mock.when_get(
        "/live/device/get/parameters/is_quantized",
        1, 1, 0
    )


# ---------------------------------------------------------------------------
# get_devices
# ---------------------------------------------------------------------------


async def test_get_devices_returns_list(mock_client: MockOscClient):
    _setup_devices(mock_client)
    result = await device_tools.get_devices(mock_client, 0)

    assert result["count"] == 2
    assert len(result["devices"]) == 2

    op = result["devices"][0]
    assert op["index"] == 0
    assert op["name"] == "Operator"
    assert op["type"] == "instrument"
    assert op["class_name"] == "Operator"

    af = result["devices"][1]
    assert af["index"] == 1
    assert af["name"] == "Auto Filter"
    assert af["type"] == "audio_effect"


async def test_get_devices_empty_track(mock_client: MockOscClient):
    mock_client.when_get("/live/track/get/num_devices", 0)
    mock_client.when_get("/live/track/get/devices/name")
    mock_client.when_get("/live/track/get/devices/type")
    mock_client.when_get("/live/track/get/devices/class_name")
    result = await device_tools.get_devices(mock_client, 0)
    assert result["count"] == 0
    assert result["devices"] == []


# ---------------------------------------------------------------------------
# get_device_parameters
# ---------------------------------------------------------------------------


async def test_get_device_parameters_returns_all(mock_client: MockOscClient):
    _setup_device_params(mock_client)
    result = await device_tools.get_device_parameters(mock_client, 0, 0)

    assert result["device_name"] == "Operator"
    assert result["count"] == 3
    assert len(result["parameters"]) == 3

    p0 = result["parameters"][0]
    assert p0["index"] == 0
    assert p0["name"] == "Device On"
    assert p0["value"] == 1.0
    assert p0["min"] == 0.0
    assert p0["max"] == 1.0
    assert p0["is_quantized"] is True

    p2 = result["parameters"][2]
    assert p2["name"] == "Filter Freq"
    assert p2["is_quantized"] is False


# ---------------------------------------------------------------------------
# get_device_parameter (single)
# ---------------------------------------------------------------------------


async def test_get_device_parameter_single(mock_client: MockOscClient):
    mock_client.when_get("/live/device/get/parameter/value", 0.75)
    mock_client.when_get("/live/device/get/parameter/value_string", "0.75 kHz")

    result = await device_tools.get_device_parameter(mock_client, 0, 0, 2)
    assert result["value"] == 0.75
    assert result["display"] == "0.75 kHz"


async def test_get_device_parameter_includes_indices(mock_client: MockOscClient):
    mock_client.when_get("/live/device/get/parameter/value", 0.5)
    mock_client.when_get("/live/device/get/parameter/value_string", "50%")
    result = await device_tools.get_device_parameter(mock_client, 1, 2, 5)
    assert result["track_index"] == 1
    assert result["device_index"] == 2
    assert result["param_index"] == 5


# ---------------------------------------------------------------------------
# set_device_parameter
# ---------------------------------------------------------------------------


async def test_set_device_parameter_sends_correct_message(mock_client: MockOscClient):
    result = await device_tools.set_device_parameter(mock_client, 0, 0, 2, 0.75)
    assert result["status"] == "ok"
    assert result["value"] == 0.75
    mock_client.assert_sent(
        "/live/device/set/parameter/value", (0, 0, 2, 0.75)
    )


async def test_set_device_parameter_preserves_indices(mock_client: MockOscClient):
    result = await device_tools.set_device_parameter(mock_client, 2, 1, 10, 0.0)
    assert result["track_index"] == 2
    assert result["device_index"] == 1
    assert result["param_index"] == 10


# ---------------------------------------------------------------------------
# Device type mapping
# ---------------------------------------------------------------------------


def test_device_type_mapping():
    assert device_tools._DEVICE_TYPES[0] == "audio_effect"
    assert device_tools._DEVICE_TYPES[1] == "instrument"
    assert device_tools._DEVICE_TYPES[2] == "midi_effect"
