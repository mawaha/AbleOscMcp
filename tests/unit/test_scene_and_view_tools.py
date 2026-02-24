"""Unit tests for scene and view tools."""

from __future__ import annotations

import pytest

from ableosc.tools import scene as scene_tools
from ableosc.tools import view as view_tools
from tests.conftest import MockOscClient, setup_default_session

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Scene tools
# ---------------------------------------------------------------------------


async def test_get_scenes_returns_all(mock_client: MockOscClient):
    setup_default_session(mock_client)
    result = await scene_tools.get_scenes(mock_client)

    assert result["count"] == 4
    assert result["scenes"][0] == {"index": 0, "name": "Intro"}
    assert result["scenes"][3] == {"index": 3, "name": "Outro"}


async def test_get_scenes_empty(mock_client: MockOscClient):
    mock_client.when_get("/live/song/get/num_scenes", 0)
    mock_client.when_get("/live/song/get/scenes/name")
    result = await scene_tools.get_scenes(mock_client)
    assert result["count"] == 0
    assert result["scenes"] == []


async def test_get_scene_single(mock_client: MockOscClient):
    # Scene-level: (scene_index, value)
    mock_client.when_get("/live/scene/get/name", 0, "Intro")
    mock_client.when_get("/live/scene/get/tempo", 0, 120.0)
    mock_client.when_get("/live/scene/get/tempo_enabled", 0, 0)

    result = await scene_tools.get_scene(mock_client, 0)
    assert result["name"] == "Intro"
    assert result["tempo"] == 120.0
    assert result["tempo_enabled"] is False


async def test_fire_scene(mock_client: MockOscClient):
    result = await scene_tools.fire_scene(mock_client, 2)
    assert result["status"] == "ok"
    assert result["scene_index"] == 2
    mock_client.assert_sent("/live/scene/fire", (2,))


async def test_create_scene(mock_client: MockOscClient):
    result = await scene_tools.create_scene(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/song/create_scene")


async def test_delete_scene(mock_client: MockOscClient):
    result = await scene_tools.delete_scene(mock_client, 3)
    assert result["deleted_scene_index"] == 3
    mock_client.assert_sent("/live/song/delete_scene", (3,))


async def test_duplicate_scene(mock_client: MockOscClient):
    result = await scene_tools.duplicate_scene(mock_client, 1)
    mock_client.assert_sent("/live/song/duplicate_scene", (1,))


async def test_set_scene_name(mock_client: MockOscClient):
    result = await scene_tools.set_scene_name(mock_client, 0, "Build Up")
    assert result["name"] == "Build Up"
    mock_client.assert_sent("/live/scene/set/name", (0, "Build Up"))


async def test_set_scene_tempo(mock_client: MockOscClient):
    result = await scene_tools.set_scene_tempo(mock_client, 1, 140.0)
    assert result["tempo"] == 140.0
    assert result["enabled"] is True
    mock_client.assert_sent("/live/scene/set/tempo", (1, 140.0))
    mock_client.assert_sent("/live/scene/set/tempo_enabled", (1, 1))


async def test_set_scene_tempo_rejects_out_of_range(mock_client: MockOscClient):
    with pytest.raises(ValueError, match="20"):
        await scene_tools.set_scene_tempo(mock_client, 0, 5.0)


async def test_set_scene_tempo_disable(mock_client: MockOscClient):
    await scene_tools.set_scene_tempo(mock_client, 0, 120.0, enabled=False)
    mock_client.assert_sent("/live/scene/set/tempo_enabled", (0, 0))


async def test_fire_selected_scene(mock_client: MockOscClient):
    result = await scene_tools.fire_selected_scene(mock_client)
    assert result["status"] == "ok"
    mock_client.assert_sent("/live/scene/fire_selected")


# ---------------------------------------------------------------------------
# View tools
# ---------------------------------------------------------------------------


async def test_get_selected_track(mock_client: MockOscClient):
    mock_client.when_get("/live/view/get/selected_track", 2)
    result = await view_tools.get_selected_track(mock_client)
    assert result["selected_track_index"] == 2


async def test_set_selected_track(mock_client: MockOscClient):
    result = await view_tools.set_selected_track(mock_client, 1)
    assert result["selected_track_index"] == 1
    mock_client.assert_sent("/live/view/set/selected_track", (1,))


async def test_get_selected_scene(mock_client: MockOscClient):
    mock_client.when_get("/live/view/get/selected_scene", 3)
    result = await view_tools.get_selected_scene(mock_client)
    assert result["selected_scene_index"] == 3


async def test_set_selected_scene(mock_client: MockOscClient):
    result = await view_tools.set_selected_scene(mock_client, 0)
    mock_client.assert_sent("/live/view/set/selected_scene", (0,))


async def test_get_selected_clip(mock_client: MockOscClient):
    mock_client.when_get("/live/view/get/selected_clip", 1, 2)
    result = await view_tools.get_selected_clip(mock_client)
    assert result["selected_track_index"] == 1
    assert result["selected_clip_index"] == 2


async def test_set_selected_clip(mock_client: MockOscClient):
    result = await view_tools.set_selected_clip(mock_client, 0, 3)
    mock_client.assert_sent("/live/view/set/selected_clip", (0, 3))


async def test_get_selected_device(mock_client: MockOscClient):
    mock_client.when_get("/live/view/get/selected_device", 0, 1)
    result = await view_tools.get_selected_device(mock_client)
    assert result["selected_track_index"] == 0
    assert result["selected_device_index"] == 1


async def test_set_selected_device(mock_client: MockOscClient):
    result = await view_tools.set_selected_device(mock_client, 2, 0)
    mock_client.assert_sent("/live/view/set/selected_device", (2, 0))
