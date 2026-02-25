"""Unit tests for ableosc.tools.device_db and ableosc.device_database."""

import json
import pytest
from pathlib import Path
from tests.conftest import MockOscClient
from ableosc.device_database import DeviceDatabase
from ableosc.tools import device_db as db_tools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path) -> DeviceDatabase:
    """DeviceDatabase backed by a temp file — isolated per test."""
    return DeviceDatabase(path=tmp_path / "device_db.json")


def _sample_params(count=5):
    return [
        {
            "index": i,
            "name": f"Param {i}",
            "value": float(i),
            "min": 0.0,
            "max": 100.0,
            "display": f"{i}",
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# DeviceDatabase — store / load
# ---------------------------------------------------------------------------

class TestDeviceDatabase:
    def test_store_and_retrieve(self, tmp_db):
        params = _sample_params(3)
        tmp_db.store("Operator", params)
        entry = tmp_db.get_device("Operator")
        assert entry is not None
        assert entry.name == "Operator"
        assert len(entry.parameters) == 3

    def test_persists_to_disk(self, tmp_path):
        db1 = DeviceDatabase(path=tmp_path / "db.json")
        db1.store("Wavetable", _sample_params(4))
        db2 = DeviceDatabase(path=tmp_path / "db.json")
        entry = db2.get_device("Wavetable")
        assert entry is not None
        assert len(entry.parameters) == 4

    def test_case_insensitive_get(self, tmp_db):
        tmp_db.store("Operator", _sample_params(2))
        assert tmp_db.get_device("operator") is not None
        assert tmp_db.get_device("OPERATOR") is not None

    def test_unknown_device_returns_none(self, tmp_db):
        assert tmp_db.get_device("NonExistent") is None

    def test_list_devices(self, tmp_db):
        tmp_db.store("Operator", _sample_params(5))
        tmp_db.store("Wavetable", _sample_params(3))
        devices = tmp_db.list_devices()
        names = [d["name"] for d in devices]
        assert "Operator" in names
        assert "Wavetable" in names

    def test_overwrite_existing(self, tmp_db):
        tmp_db.store("Operator", _sample_params(5))
        tmp_db.store("Operator", _sample_params(10))
        entry = tmp_db.get_device("Operator")
        assert len(entry.parameters) == 10

    def test_corrupt_file_starts_fresh(self, tmp_path):
        p = tmp_path / "db.json"
        p.write_text("not valid json")
        db = DeviceDatabase(path=p)
        assert db.list_devices() == []


# ---------------------------------------------------------------------------
# DeviceDatabase — lookup_parameter
# ---------------------------------------------------------------------------

class TestLookupParameter:
    @pytest.fixture
    def db_with_operator(self, tmp_db):
        params = [
            {"index": 0, "name": "Pitch", "value": 0.0, "min": -48.0, "max": 48.0, "display": "0 st"},
            {"index": 1, "name": "Filter Cutoff", "value": 0.5, "min": 0.0, "max": 1.0, "display": "50%"},
            {"index": 2, "name": "Filter Resonance", "value": 0.0, "min": 0.0, "max": 1.0, "display": "0%"},
            {"index": 3, "name": "Amp Attack", "value": 0.01, "min": 0.001, "max": 60.0, "display": "10ms"},
            {"index": 4, "name": "Amp Decay", "value": 0.5, "min": 0.001, "max": 60.0, "display": "500ms"},
            {"index": 5, "name": "LFO Rate", "value": 1.0, "min": 0.01, "max": 20.0, "display": "1 Hz"},
        ]
        tmp_db.store("Operator", params)
        return tmp_db

    def test_exact_match(self, db_with_operator):
        results = db_with_operator.lookup_parameter("Operator", "Filter Cutoff")
        assert len(results) >= 1
        assert results[0]["index"] == 1
        assert results[0]["match_quality"] == "exact"

    def test_case_insensitive_exact(self, db_with_operator):
        results = db_with_operator.lookup_parameter("Operator", "filter cutoff")
        assert results[0]["match_quality"] == "exact"
        assert results[0]["index"] == 1

    def test_starts_with(self, db_with_operator):
        results = db_with_operator.lookup_parameter("Operator", "Filter")
        names = [r["name"] for r in results]
        assert "Filter Cutoff" in names
        assert "Filter Resonance" in names

    def test_contains(self, db_with_operator):
        results = db_with_operator.lookup_parameter("Operator", "Cutoff")
        assert any(r["name"] == "Filter Cutoff" for r in results)

    def test_word_match(self, db_with_operator):
        results = db_with_operator.lookup_parameter("Operator", "amp attack")
        assert results[0]["name"] == "Amp Attack"

    def test_no_match_returns_empty(self, db_with_operator):
        results = db_with_operator.lookup_parameter("Operator", "xyz_nonexistent")
        assert results == []

    def test_unknown_device_raises(self, db_with_operator):
        with pytest.raises(KeyError, match="not in database"):
            db_with_operator.lookup_parameter("NonExistentDevice", "cutoff")


# ---------------------------------------------------------------------------
# catalog_device tool
# ---------------------------------------------------------------------------

class TestCatalogDevice:
    async def test_catalogs_from_live(self, tmp_db):
        client = MockOscClient()
        # get_device_parameters makes 7 concurrent gets — mock them all
        client.when_get("/live/device/get/name", 0, 0, "Operator")
        client.when_get("/live/device/get/num_parameters", 0, 0, 2)
        # List responses: (track_index, device_index, val1, val2, ...)
        client.when_get("/live/device/get/parameters/name", 0, 0, "Filter Cutoff", "Filter Res")
        client.when_get("/live/device/get/parameters/value", 0, 0, 0.5, 0.0)
        client.when_get("/live/device/get/parameters/min", 0, 0, 0.0, 0.0)
        client.when_get("/live/device/get/parameters/max", 0, 0, 1.0, 1.0)
        client.when_get("/live/device/get/parameters/is_quantized", 0, 0, 0, 0)

        result = await db_tools.catalog_device(client, tmp_db, 0, 0)
        assert result["device_name"] == "Operator"
        assert result["parameter_count"] == 2
        assert result["status"] == "cataloged"
        # Verify stored in DB
        entry = tmp_db.get_device("Operator")
        assert entry is not None
        assert entry.parameters[0].name == "Filter Cutoff"


# ---------------------------------------------------------------------------
# list_known_devices tool
# ---------------------------------------------------------------------------

class TestListKnownDevices:
    async def test_empty_db(self, tmp_db):
        result = await db_tools.list_known_devices(tmp_db)
        assert result["count"] == 0
        assert result["devices"] == []

    async def test_lists_all_devices(self, tmp_db):
        tmp_db.store("Operator", _sample_params(5))
        tmp_db.store("Wavetable", _sample_params(3))
        result = await db_tools.list_known_devices(tmp_db)
        assert result["count"] == 2
        names = [d["name"] for d in result["devices"]]
        assert "Operator" in names
        assert "Wavetable" in names


# ---------------------------------------------------------------------------
# lookup_parameter tool
# ---------------------------------------------------------------------------

class TestLookupParameterTool:
    async def test_returns_matches(self, tmp_db):
        params = [
            {"index": 1, "name": "Filter Cutoff", "value": 0.5, "min": 0.0, "max": 1.0, "display": "50%"},
        ]
        tmp_db.store("Operator", params)
        result = await db_tools.lookup_parameter(tmp_db, "Operator", "filter")
        assert result["count"] >= 1
        assert result["device_name"] == "Operator"
        assert result["query"] == "filter"

    async def test_unknown_device_raises(self, tmp_db):
        with pytest.raises(KeyError):
            await db_tools.lookup_parameter(tmp_db, "Ghost", "cutoff")


# ---------------------------------------------------------------------------
# set_device_parameter_by_name tool
# ---------------------------------------------------------------------------

class TestSetDeviceParameterByName:
    async def test_sets_correct_index(self, tmp_db):
        params = [
            {"index": 0, "name": "Pitch", "value": 0.0, "min": -48.0, "max": 48.0, "display": "0"},
            {"index": 3, "name": "Filter Cutoff", "value": 0.5, "min": 0.0, "max": 1.0, "display": "50%"},
        ]
        tmp_db.store("Operator", params)
        client = MockOscClient()

        result = await db_tools.set_device_parameter_by_name(
            client, tmp_db, 0, 0, "Operator", "filter cutoff", 0.75
        )
        assert result["param_index"] == 3
        assert result["param_name"] == "Filter Cutoff"
        assert result["value"] == 0.75
        # Verify OSC was sent with correct index
        client.assert_sent("/live/device/set/parameter/value", (0, 0, 3, 0.75))

    async def test_no_match_raises(self, tmp_db):
        tmp_db.store("Operator", _sample_params(2))
        client = MockOscClient()
        with pytest.raises(ValueError, match="No parameter matching"):
            await db_tools.set_device_parameter_by_name(
                client, tmp_db, 0, 0, "Operator", "nonexistent_xyz", 0.5
            )
