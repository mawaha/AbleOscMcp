"""
Persistent database of Ableton device parameters.

Stores parameter metadata (index, name, min, max, value, display) for each
named device so Claude can look up parameters by name instead of guessing indices.

Database lives at ~/.ableosc/device_db.json — user-level, persists across sessions.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ParameterEntry:
    index: int
    name: str
    value: float
    min: float
    max: float
    display: str
    info_title: str = ""   # Info View title e.g. "Filter Frequency"
    info_text: str = ""    # Info View description e.g. "This defines the center or cutoff frequency..."


@dataclass
class DeviceEntry:
    name: str
    cataloged_at: str
    parameters: list[ParameterEntry]


def _default_db_path() -> Path:
    return Path.home() / ".ableosc" / "device_db.json"


class DeviceDatabase:
    """
    JSON-backed store mapping device names to their parameter lists.

    Usage:
        db = DeviceDatabase()
        db.store("Operator", params_list)
        entry = db.lookup_parameter("Operator", "filter cutoff")
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _default_db_path()
        self._data: dict[str, DeviceEntry] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            for name, entry in raw.get("devices", {}).items():
                params = [
                    ParameterEntry(
                        index=p["index"],
                        name=p["name"],
                        value=p["value"],
                        min=p["min"],
                        max=p["max"],
                        display=p.get("display", ""),
                        info_title=p.get("info_title", ""),
                        info_text=p.get("info_text", ""),
                    )
                    for p in entry["parameters"]
                ]
                self._data[name] = DeviceEntry(
                    name=entry["name"],
                    cataloged_at=entry["cataloged_at"],
                    parameters=params,
                )
        except Exception:
            # Corrupt file — start fresh
            self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"devices": {}}
        for name, entry in self._data.items():
            payload["devices"][name] = {
                "name": entry.name,
                "cataloged_at": entry.cataloged_at,
                "parameters": [asdict(p) for p in entry.parameters],
            }
        self._path.write_text(json.dumps(payload, indent=2))

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def store(self, device_name: str, parameters: list[dict[str, Any]]) -> DeviceEntry:
        """
        Store a device's parameter list in the database.

        parameters: list of dicts with keys index, name, value, min, max, display
        """
        params = [
            ParameterEntry(
                index=p["index"],
                name=p["name"],
                value=float(p.get("value", 0)),
                min=float(p.get("min", 0)),
                max=float(p.get("max", 1)),
                display=str(p.get("display", "")),
                info_title=str(p.get("info_title", "")),
                info_text=str(p.get("info_text", "")),
            )
            for p in parameters
        ]
        entry = DeviceEntry(
            name=device_name,
            cataloged_at=datetime.now(timezone.utc).isoformat(),
            parameters=params,
        )
        self._data[device_name] = entry
        self._save()
        return entry

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_devices(self) -> list[dict[str, Any]]:
        """Return summary of all catalogued devices."""
        return [
            {
                "name": e.name,
                "parameter_count": len(e.parameters),
                "cataloged_at": e.cataloged_at,
            }
            for e in self._data.values()
        ]

    def get_device(self, device_name: str) -> DeviceEntry | None:
        """Return full device entry or None if not found."""
        # Exact match first
        if device_name in self._data:
            return self._data[device_name]
        # Case-insensitive match
        lower = device_name.lower()
        for key, entry in self._data.items():
            if key.lower() == lower:
                return entry
        return None

    def lookup_parameter(
        self, device_name: str, param_name: str
    ) -> list[dict[str, Any]]:
        """
        Fuzzy-search for a parameter by name within a device.

        Returns all matching parameters sorted by match quality.
        Matches: exact (case-insensitive) > starts-with > contains (each word).
        """
        entry = self.get_device(device_name)
        if entry is None:
            raise KeyError(
                f"Device {device_name!r} not in database. "
                f"Known devices: {[e.name for e in self._data.values()]}"
            )

        needle = param_name.lower().strip()
        results: list[tuple[int, ParameterEntry]] = []

        for p in entry.parameters:
            haystack = p.name.lower()
            if haystack == needle:
                score = 0
            elif haystack.startswith(needle):
                score = 1
            elif needle in haystack:
                score = 2
            elif all(word in haystack for word in needle.split()):
                score = 3
            else:
                continue
            results.append((score, p))

        results.sort(key=lambda x: (x[0], x[1].index))
        return [
            {
                "index": p.index,
                "name": p.name,
                "value": p.value,
                "min": p.min,
                "max": p.max,
                "display": p.display,
                "info_title": p.info_title,
                "info_text": p.info_text,
                "match_quality": ["exact", "starts_with", "contains", "words"][score],
            }
            for score, p in results
        ]

    def annotate_parameter(
        self,
        device_name: str,
        param_index: int,
        info_title: str,
        info_text: str,
    ) -> bool:
        """
        Add or update the Info View title and description for a parameter.

        Returns True if the parameter was found and updated, False otherwise.
        """
        entry = self.get_device(device_name)
        if entry is None:
            return False
        for p in entry.parameters:
            if p.index == param_index:
                p.info_title = info_title
                p.info_text = info_text
                self._save()
                return True
        return False
