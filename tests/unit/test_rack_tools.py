"""Unit tests for rack chain traversal tools."""

from __future__ import annotations

import pytest

from ableosc.tools import rack as rack_tools
from tests.conftest import MockOscClient

pytestmark = pytest.mark.unit


def _setup_rack(
    mock: MockOscClient,
    track_index: int = 0,
    device_index: int = 0,
    chain_names: list[str] | None = None,
) -> None:
    """Pre-load responses for a rack device."""
    if chain_names is None:
        chain_names = ["Bright", "Warm"]
    count = len(chain_names)
    mock.when_get("/live/rack/get/num_chains", track_index, device_index, count)
    mock.when_get("/live/rack/get/chains/name", track_index, device_index, *chain_names)


def _setup_chain(
    mock: MockOscClient,
    track_index: int = 0,
    device_index: int = 0,
    chain_index: int = 0,
    device_names: list[str] | None = None,
    class_names: list[str] | None = None,
    can_have_chains: list[int] | None = None,
) -> None:
    """Pre-load responses for a rack chain."""
    if device_names is None:
        device_names = ["Operator"]
    if class_names is None:
        class_names = ["InstrumentGroupDevice" if d == "Rack" else "OriginalSimpler"
                       for d in device_names]
    if can_have_chains is None:
        can_have_chains = [0] * len(device_names)
    count = len(device_names)

    mock.when_get("/live/rack/get/chain/num_devices",
                  track_index, device_index, chain_index, count)
    mock.when_get("/live/rack/get/chain/devices/name",
                  track_index, device_index, chain_index, *device_names)
    mock.when_get("/live/rack/get/chain/devices/class_name",
                  track_index, device_index, chain_index, *class_names)
    mock.when_get("/live/rack/get/chain/devices/can_have_chains",
                  track_index, device_index, chain_index, *can_have_chains)


def _setup_chain_device(
    mock: MockOscClient,
    track_index: int = 0,
    device_index: int = 0,
    chain_index: int = 0,
    nested_device_index: int = 0,
    device_name: str = "Operator",
    params: list[tuple] | None = None,
) -> None:
    """Pre-load responses for a nested device.

    Each param tuple: (name, value, min, max, is_quantized)
    """
    if params is None:
        params = [
            ("Filter Freq", 0.5, 0.0, 1.0, 0),
            ("Resonance", 0.3, 0.0, 1.0, 0),
        ]

    ids = (track_index, device_index, chain_index, nested_device_index)
    count = len(params)

    mock.when_get("/live/rack/get/chain/device/name", *ids, device_name)
    mock.when_get("/live/rack/get/chain/device/num_parameters", *ids, count)
    mock.when_get("/live/rack/get/chain/device/parameters/name",
                  *ids, *[p[0] for p in params])
    mock.when_get("/live/rack/get/chain/device/parameters/value",
                  *ids, *[p[1] for p in params])
    mock.when_get("/live/rack/get/chain/device/parameters/min",
                  *ids, *[p[2] for p in params])
    mock.when_get("/live/rack/get/chain/device/parameters/max",
                  *ids, *[p[3] for p in params])
    mock.when_get("/live/rack/get/chain/device/parameters/is_quantized",
                  *ids, *[p[4] for p in params])


# ---------------------------------------------------------------------------
# get_rack_chains
# ---------------------------------------------------------------------------


async def test_get_rack_chains_returns_count_and_names(mock_client: MockOscClient):
    _setup_rack(mock_client, chain_names=["Bright", "Warm", "Dark"])
    result = await rack_tools.get_rack_chains(mock_client, 0, 0)

    assert result["count"] == 3
    assert len(result["chains"]) == 3
    assert result["chains"][0] == {"index": 0, "name": "Bright"}
    assert result["chains"][1] == {"index": 1, "name": "Warm"}
    assert result["chains"][2] == {"index": 2, "name": "Dark"}


async def test_get_rack_chains_includes_indices(mock_client: MockOscClient):
    _setup_rack(mock_client, track_index=2, device_index=1)
    result = await rack_tools.get_rack_chains(mock_client, 2, 1)

    assert result["track_index"] == 2
    assert result["device_index"] == 1


async def test_get_rack_chains_empty(mock_client: MockOscClient):
    mock_client.when_get("/live/rack/get/num_chains", 0, 0, 0)
    mock_client.when_get("/live/rack/get/chains/name", 0, 0)
    result = await rack_tools.get_rack_chains(mock_client, 0, 0)

    assert result["count"] == 0
    assert result["chains"] == []


# ---------------------------------------------------------------------------
# get_chain_devices
# ---------------------------------------------------------------------------


async def test_get_chain_devices_returns_device_list(mock_client: MockOscClient):
    _setup_chain(mock_client, device_names=["Operator", "Auto Filter"])
    result = await rack_tools.get_chain_devices(mock_client, 0, 0, 0)

    assert result["count"] == 2
    assert len(result["devices"]) == 2
    assert result["devices"][0]["index"] == 0
    assert result["devices"][0]["name"] == "Operator"
    assert result["devices"][1]["name"] == "Auto Filter"


async def test_get_chain_devices_includes_class_name(mock_client: MockOscClient):
    _setup_chain(
        mock_client,
        device_names=["Operator"],
        class_names=["OriginalOperator"],
        can_have_chains=[0],
    )
    result = await rack_tools.get_chain_devices(mock_client, 0, 0, 0)

    assert result["devices"][0]["class_name"] == "OriginalOperator"
    assert result["devices"][0]["can_have_chains"] is False


async def test_get_chain_devices_flags_nested_rack(mock_client: MockOscClient):
    _setup_chain(
        mock_client,
        device_names=["Inner Rack"],
        class_names=["InstrumentGroupDevice"],
        can_have_chains=[1],
    )
    result = await rack_tools.get_chain_devices(mock_client, 0, 0, 0)

    assert result["devices"][0]["can_have_chains"] is True


async def test_get_chain_devices_includes_coords(mock_client: MockOscClient):
    _setup_chain(mock_client, track_index=1, device_index=2, chain_index=3)
    result = await rack_tools.get_chain_devices(mock_client, 1, 2, 3)

    assert result["track_index"] == 1
    assert result["device_index"] == 2
    assert result["chain_index"] == 3


# ---------------------------------------------------------------------------
# get_chain_device_parameters
# ---------------------------------------------------------------------------


async def test_get_chain_device_parameters_returns_all_fields(mock_client: MockOscClient):
    _setup_chain_device(mock_client, device_name="Operator")
    result = await rack_tools.get_chain_device_parameters(mock_client, 0, 0, 0, 0)

    assert result["device_name"] == "Operator"
    assert result["count"] == 2
    assert len(result["parameters"]) == 2


async def test_get_chain_device_parameters_field_values(mock_client: MockOscClient):
    _setup_chain_device(
        mock_client,
        params=[("Filter Freq", 0.5, 0.0, 1.0, 0)],
    )
    result = await rack_tools.get_chain_device_parameters(mock_client, 0, 0, 0, 0)
    param = result["parameters"][0]

    assert param["index"] == 0
    assert param["name"] == "Filter Freq"
    assert param["value"] == pytest.approx(0.5)
    assert param["min"] == 0.0
    assert param["max"] == 1.0
    assert param["is_quantized"] is False


async def test_get_chain_device_parameters_zero_params(mock_client: MockOscClient):
    _setup_chain_device(mock_client, params=[])
    result = await rack_tools.get_chain_device_parameters(mock_client, 0, 0, 0, 0)

    assert result["count"] == 0
    assert result["parameters"] == []


async def test_get_chain_device_parameters_includes_coords(mock_client: MockOscClient):
    _setup_chain_device(mock_client, track_index=1, device_index=2,
                        chain_index=3, nested_device_index=0)
    result = await rack_tools.get_chain_device_parameters(mock_client, 1, 2, 3, 0)

    assert result["track_index"] == 1
    assert result["device_index"] == 2
    assert result["chain_index"] == 3
    assert result["nested_device_index"] == 0


# ---------------------------------------------------------------------------
# set_chain_device_parameter
# ---------------------------------------------------------------------------


async def test_set_chain_device_parameter_sends_correct_message(mock_client: MockOscClient):
    result = await rack_tools.set_chain_device_parameter(mock_client, 0, 0, 0, 0, 3, 0.75)

    assert result["status"] == "ok"
    assert result["param_index"] == 3
    assert result["value"] == 0.75
    mock_client.assert_sent(
        "/live/rack/set/chain/device/parameter/value",
        (0, 0, 0, 0, 3, 0.75),
    )


async def test_set_chain_device_parameter_returns_all_coords(mock_client: MockOscClient):
    result = await rack_tools.set_chain_device_parameter(mock_client, 2, 1, 0, 0, 5, 0.5)

    assert result["track_index"] == 2
    assert result["device_index"] == 1
    assert result["chain_index"] == 0
    assert result["nested_device_index"] == 0


# ---------------------------------------------------------------------------
# _scalar helper
# ---------------------------------------------------------------------------


def test_scalar_rack_level():
    assert rack_tools._scalar((0, 0, 3)) == 3


def test_scalar_chain_level():
    assert rack_tools._scalar((0, 0, 1, 2)) == 2


def test_scalar_chain_device_level():
    assert rack_tools._scalar((0, 0, 0, 0, "Operator")) == "Operator"


def test_scalar_empty():
    assert rack_tools._scalar(()) is None
