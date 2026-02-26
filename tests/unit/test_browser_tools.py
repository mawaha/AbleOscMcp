"""Unit tests for browser tools."""

from __future__ import annotations

import pytest

from ableosc.tools import browser_tools
from tests.conftest import MockOscClient

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# list_browser_categories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_browser_categories_returns_dict():
    mock = MockOscClient()
    mock.when_get(
        "/live/browser/get/categories",
        "instruments",
        "audio_effects",
        "midi_effects",
        "plugins",
        "sounds",
        "drums",
        "user_library",
    )
    result = await browser_tools.list_browser_categories(mock)
    assert "categories" in result
    assert "instruments" in result["categories"]
    assert "audio_effects" in result["categories"]


@pytest.mark.asyncio
async def test_list_browser_categories_all_keys():
    mock = MockOscClient()
    expected = ["instruments", "audio_effects", "midi_effects", "plugins",
                "sounds", "drums", "user_library"]
    mock.when_get("/live/browser/get/categories", *expected)
    result = await browser_tools.list_browser_categories(mock)
    assert result["categories"] == expected


@pytest.mark.asyncio
async def test_list_browser_categories_sends_correct_address():
    mock = MockOscClient()
    mock.when_get("/live/browser/get/categories", "instruments")
    await browser_tools.list_browser_categories(mock)
    assert any(addr == "/live/browser/get/categories" for addr, _ in mock.gets)


# ---------------------------------------------------------------------------
# list_browser_devices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_browser_devices_returns_category_and_devices():
    mock = MockOscClient()
    mock.when_get("/live/browser/get/devices", "Analog", "Wavetable", "Operator")
    result = await browser_tools.list_browser_devices(mock, "instruments")
    assert result["category"] == "instruments"
    assert result["devices"] == ["Analog", "Wavetable", "Operator"]


@pytest.mark.asyncio
async def test_list_browser_devices_sends_category_param():
    mock = MockOscClient()
    mock.when_get("/live/browser/get/devices", "Auto Filter", "Compressor")
    await browser_tools.list_browser_devices(mock, "audio_effects")
    assert any(
        addr == "/live/browser/get/devices" and args == ("audio_effects",)
        for addr, args in mock.gets
    )


@pytest.mark.asyncio
async def test_list_browser_devices_empty_category():
    mock = MockOscClient()
    mock.when_get("/live/browser/get/devices")  # empty response
    result = await browser_tools.list_browser_devices(mock, "drums")
    assert result["devices"] == []


# ---------------------------------------------------------------------------
# load_device
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_device_success():
    mock = MockOscClient()
    mock.when_get("/live/browser/load", 1, "Analog")
    result = await browser_tools.load_device(mock, 0, "instruments", "Analog")
    assert result["loaded"] is True
    assert result["name"] == "Analog"


@pytest.mark.asyncio
async def test_load_device_not_found():
    mock = MockOscClient()
    mock.when_get("/live/browser/load", 0)  # failure response
    result = await browser_tools.load_device(mock, 0, "instruments", "NonExistentDevice")
    assert result["loaded"] is False


@pytest.mark.asyncio
async def test_load_device_sends_correct_params():
    mock = MockOscClient()
    mock.when_get("/live/browser/load", 1, "Wavetable")
    await browser_tools.load_device(mock, 2, "instruments", "Wavetable")
    assert any(
        addr == "/live/browser/load" and args == (2, "instruments", "Wavetable")
        for addr, args in mock.gets
    )


@pytest.mark.asyncio
async def test_load_device_audio_effect():
    mock = MockOscClient()
    mock.when_get("/live/browser/load", 1, "Auto Filter")
    result = await browser_tools.load_device(mock, 0, "audio_effects", "Auto Filter")
    assert result["loaded"] is True
    assert result["name"] == "Auto Filter"


@pytest.mark.asyncio
async def test_load_device_partial_name_match():
    """Server does partial matching — we just check the returned name is used."""
    mock = MockOscClient()
    mock.when_get("/live/browser/load", 1, "Auto Filter")
    result = await browser_tools.load_device(mock, 1, "audio_effects", "filter")
    assert result["loaded"] is True
    assert result["name"] == "Auto Filter"
