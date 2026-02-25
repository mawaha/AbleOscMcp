"""Unit tests for MCP resource builder functions."""

from __future__ import annotations

import pytest

from ableosc import resources
from tests.conftest import MockOscClient, setup_default_session

pytestmark = pytest.mark.unit


def _setup_track(mock: MockOscClient, track_index: int = 0) -> None:
    """Pre-load realistic responses for a single track."""
    mock.when_get("/live/track/get/name", track_index, "Drums")
    mock.when_get("/live/track/get/volume", track_index, 0.85)
    mock.when_get("/live/track/get/panning", track_index, 0.0)
    mock.when_get("/live/track/get/mute", track_index, 0)
    mock.when_get("/live/track/get/solo", track_index, 0)
    mock.when_get("/live/track/get/arm", track_index, 1)
    mock.when_get("/live/track/get/can_be_armed", track_index, 1)
    mock.when_get("/live/track/get/num_devices", track_index, 1)
    mock.when_get("/live/track/get/devices/name", track_index, "Drum Rack")
    mock.when_get("/live/track/get/clips/name", track_index, "Beat Loop", None, None, None)


def _setup_device(
    mock: MockOscClient,
    track_index: int = 0,
    device_index: int = 0,
    device_name: str = "Operator",
    params: list[tuple] | None = None,
) -> None:
    """Pre-load responses for get_device_parameters.

    Each param tuple: (name, value, min, max, is_quantized)
    """
    if params is None:
        params = [
            ("Filter Freq", 0.5, 0.0, 1.0, 0),
            ("Resonance", 0.3, 0.0, 1.0, 0),
        ]

    count = len(params)
    param_names = [p[0] for p in params]
    param_values = [p[1] for p in params]
    param_mins = [p[2] for p in params]
    param_maxs = [p[3] for p in params]
    param_quantized = [p[4] for p in params]

    mock.when_get("/live/device/get/name", track_index, device_index, device_name)
    mock.when_get("/live/device/get/num_parameters", track_index, device_index, count)
    mock.when_get("/live/device/get/parameters/name", track_index, device_index, *param_names)
    mock.when_get("/live/device/get/parameters/value", track_index, device_index, *param_values)
    mock.when_get("/live/device/get/parameters/min", track_index, device_index, *param_mins)
    mock.when_get("/live/device/get/parameters/max", track_index, device_index, *param_maxs)
    mock.when_get(
        "/live/device/get/parameters/is_quantized", track_index, device_index, *param_quantized
    )


# ---------------------------------------------------------------------------
# session_state
# ---------------------------------------------------------------------------


async def test_session_state_includes_tempo_and_playback(mock_client: MockOscClient):
    setup_default_session(mock_client)
    result = await resources.session_state(mock_client)

    assert result["tempo"] == 120.0
    assert result["time_signature"] == "4/4"
    assert result["is_playing"] is False
    assert result["num_tracks"] == 3
    assert result["num_scenes"] == 4


async def test_session_state_includes_tracks_list(mock_client: MockOscClient):
    setup_default_session(mock_client)
    result = await resources.session_state(mock_client)

    assert "tracks" in result
    assert len(result["tracks"]) == 3
    assert result["tracks"][0] == {"index": 0, "name": "Drums"}
    assert result["tracks"][1] == {"index": 1, "name": "Bass"}
    assert result["tracks"][2] == {"index": 2, "name": "Lead"}


async def test_session_state_includes_loop_info(mock_client: MockOscClient):
    setup_default_session(mock_client)
    result = await resources.session_state(mock_client)

    assert "loop" in result
    assert result["loop"]["enabled"] is False
    assert result["loop"]["start_beats"] == 0.0
    assert result["loop"]["length_beats"] == 4.0


# ---------------------------------------------------------------------------
# session_tracks
# ---------------------------------------------------------------------------


async def test_session_tracks_single_track(mock_client: MockOscClient):
    mock_client.when_get("/live/song/get/num_tracks", 1)
    mock_client.when_get("/live/song/get/track_names", "Drums")
    _setup_track(mock_client, 0)

    result = await resources.session_tracks(mock_client)

    assert result["count"] == 1
    assert len(result["tracks"]) == 1
    track = result["tracks"][0]
    assert track["index"] == 0
    assert track["name"] == "Drums"
    assert track["volume"] == pytest.approx(0.85)
    assert track["pan"] == 0.0
    assert track["mute"] is False
    assert track["arm"] is True
    assert track["devices"] == ["Drum Rack"]
    assert len(track["clips"]) == 1


async def test_session_tracks_two_tracks(mock_client: MockOscClient):
    mock_client.when_get("/live/song/get/num_tracks", 2)
    mock_client.when_get("/live/song/get/track_names", "Drums", "Bass")
    _setup_track(mock_client, 0)  # mock responses used for both tracks

    result = await resources.session_tracks(mock_client)

    assert result["count"] == 2
    assert len(result["tracks"]) == 2


async def test_session_tracks_empty_session(mock_client: MockOscClient):
    mock_client.when_get("/live/song/get/num_tracks", 0)
    mock_client.when_get("/live/song/get/track_names")

    result = await resources.session_tracks(mock_client)

    assert result["count"] == 0
    assert result["tracks"] == []


# ---------------------------------------------------------------------------
# device_resource
# ---------------------------------------------------------------------------


async def test_device_resource_returns_parameters(mock_client: MockOscClient):
    _setup_device(mock_client, track_index=0, device_index=0, device_name="Operator")

    result = await resources.device_resource(mock_client, 0, 0)

    assert result["device_name"] == "Operator"
    assert result["track_index"] == 0
    assert result["device_index"] == 0
    assert result["count"] == 2
    assert len(result["parameters"]) == 2


async def test_device_resource_parameter_fields(mock_client: MockOscClient):
    _setup_device(
        mock_client,
        params=[("Filter Freq", 0.5, 0.0, 1.0, 0)],
    )

    result = await resources.device_resource(mock_client, 0, 0)
    param = result["parameters"][0]

    assert param["index"] == 0
    assert param["name"] == "Filter Freq"
    assert param["value"] == pytest.approx(0.5)
    assert param["min"] == 0.0
    assert param["max"] == 1.0
    assert param["is_quantized"] is False


async def test_device_resource_zero_parameters(mock_client: MockOscClient):
    _setup_device(mock_client, params=[])

    result = await resources.device_resource(mock_client, 0, 0)

    assert result["count"] == 0
    assert result["parameters"] == []


async def test_device_resource_correct_indices(mock_client: MockOscClient):
    _setup_device(mock_client, track_index=2, device_index=1, device_name="Auto Filter")

    result = await resources.device_resource(mock_client, 2, 1)

    assert result["track_index"] == 2
    assert result["device_index"] == 1
    assert result["device_name"] == "Auto Filter"
