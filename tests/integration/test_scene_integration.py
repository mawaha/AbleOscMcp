"""Integration tests for scene-level tools."""

from __future__ import annotations

import asyncio

import pytest

from ableosc.client import OscClient
from ableosc.tools import scene as scene_tools

pytestmark = pytest.mark.integration


@pytest.fixture()
async def test_scene(live_client: OscClient):
    """Create a temporary scene; yield its index; delete it on teardown."""
    before = await scene_tools.get_scenes(live_client)
    expected_index = before["count"]

    await scene_tools.create_scene(live_client)
    await asyncio.sleep(0.1)

    scenes = await scene_tools.get_scenes(live_client)
    assert scenes["count"] == expected_index + 1, "Scene was not created"

    yield expected_index

    try:
        await scene_tools.delete_scene(live_client, expected_index)
        await asyncio.sleep(0.05)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Scene listing
# ---------------------------------------------------------------------------

async def test_get_scenes_returns_list(live_client: OscClient):
    result = await scene_tools.get_scenes(live_client)
    assert "scenes" in result
    assert isinstance(result["scenes"], list)
    assert result["count"] == len(result["scenes"])
    for scene in result["scenes"]:
        assert "index" in scene
        assert "name" in scene


async def test_get_scene_returns_expected_fields(live_client: OscClient):
    result = await scene_tools.get_scene(live_client, 0)
    assert isinstance(result["name"], str)
    assert isinstance(result["tempo_enabled"], bool)


# ---------------------------------------------------------------------------
# Scene creation / deletion
# ---------------------------------------------------------------------------

async def test_create_scene_increases_count(live_client: OscClient):
    before = await scene_tools.get_scenes(live_client)
    await scene_tools.create_scene(live_client)
    await asyncio.sleep(0.1)
    after = await scene_tools.get_scenes(live_client)
    assert after["count"] == before["count"] + 1
    # cleanup
    await scene_tools.delete_scene(live_client, after["count"] - 1)


async def test_delete_scene_decreases_count(live_client: OscClient, test_scene: int):
    before = await scene_tools.get_scenes(live_client)
    await scene_tools.delete_scene(live_client, test_scene)
    await asyncio.sleep(0.1)
    after = await scene_tools.get_scenes(live_client)
    assert after["count"] == before["count"] - 1


async def test_duplicate_scene_increases_count(live_client: OscClient, test_scene: int):
    before = await scene_tools.get_scenes(live_client)
    await scene_tools.duplicate_scene(live_client, test_scene)
    await asyncio.sleep(0.1)
    after = await scene_tools.get_scenes(live_client)
    assert after["count"] == before["count"] + 1
    # cleanup duplicate
    await scene_tools.delete_scene(live_client, after["count"] - 1)


# ---------------------------------------------------------------------------
# Scene properties
# ---------------------------------------------------------------------------

async def test_set_scene_name(live_client: OscClient, test_scene: int):
    await scene_tools.set_scene_name(live_client, test_scene, "IntegrationScene")
    result = await scene_tools.get_scene(live_client, test_scene)
    assert result["name"] == "IntegrationScene"


async def test_set_scene_tempo(live_client: OscClient, test_scene: int):
    await scene_tools.set_scene_tempo(live_client, test_scene, 130.0, enabled=True)
    result = await scene_tools.get_scene(live_client, test_scene)
    assert result["tempo_enabled"] is True
    assert abs(result["tempo"] - 130.0) < 0.5


async def test_set_scene_tempo_rejects_out_of_range(live_client: OscClient, test_scene: int):
    with pytest.raises(ValueError):
        await scene_tools.set_scene_tempo(live_client, test_scene, 10.0)


# ---------------------------------------------------------------------------
# Fire scene
# ---------------------------------------------------------------------------

async def test_fire_scene_does_not_raise(live_client: OscClient):
    result = await scene_tools.fire_scene(live_client, 0)
    assert result["status"] == "ok"
