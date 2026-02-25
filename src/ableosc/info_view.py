"""
Ableton Info View reader using macOS Accessibility API.

Reads the title and description text from Ableton's Info View panel —
the same text shown when hovering over any control in Ableton Live.

Requirements:
    - macOS only
    - The process (or Terminal) must be granted Accessibility access in:
      System Settings → Privacy & Security → Accessibility
    - Ableton Live must be running

Usage:
    text = read_info_view()
    # {"title": "Filter Frequency", "text": "This defines the center..."}
"""

from __future__ import annotations

import sys


def is_available() -> bool:
    """Return True if the Accessibility API is available and permitted."""
    if sys.platform != "darwin":
        return False
    try:
        import Quartz  # noqa: F401
        return True
    except ImportError:
        return False


def read_info_view(app_name: str = "Live") -> dict[str, str] | None:
    """
    Read the current Info View title and text from Ableton Live.

    Returns a dict {"title": str, "text": str} or None if unavailable.

    Raises:
        RuntimeError: If not on macOS or Accessibility is not permitted.
        ImportError: If pyobjc is not installed.
    """
    if sys.platform != "darwin":
        raise RuntimeError("Info View reading is only supported on macOS")

    try:
        import Quartz
        from ApplicationServices import (
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
            AXUIElementCopyAttributeNames,
            kAXErrorSuccess,
        )
    except ImportError:
        raise ImportError(
            "pyobjc is required for Info View reading. "
            "Install with: pip install pyobjc-framework-ApplicationServices"
        )

    # Find the Live process
    pid = _find_pid(app_name)
    if pid is None:
        return None

    app_ref = AXUIElementCreateApplication(pid)

    # Walk the accessibility tree looking for the Info View panel
    title, text = _find_info_view(app_ref, AXUIElementCopyAttributeValue)
    if title is None and text is None:
        return None
    return {"title": title or "", "text": text or ""}


def _find_pid(app_name: str) -> int | None:
    """Find the PID of a running application by name."""
    import subprocess
    result = subprocess.run(
        ["pgrep", "-x", app_name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        pids = result.stdout.strip().split()
        if pids:
            return int(pids[0])
    return None


def _get_attr(element, attr: str, get_fn):
    """Get an accessibility attribute value, returning None on failure."""
    err, value = get_fn(element, attr, None)
    if err == 0:  # kAXErrorSuccess
        return value
    return None


def _find_info_view(app_ref, get_fn, depth: int = 0) -> tuple[str | None, str | None]:
    """
    Recursively walk Ableton's accessibility tree to find Info View text.

    Ableton's Info View is a static text area. We look for two adjacent
    static text elements — the title (shorter) and the body (longer).
    The Info View panel typically appears near the bottom of the main window.
    """
    if depth > 8:
        return None, None

    children = _get_attr(app_ref, "AXChildren", get_fn)
    if not children:
        return None, None

    static_texts = []
    for child in children:
        role = _get_attr(child, "AXRole", get_fn)

        if role == "AXStaticText":
            value = _get_attr(child, "AXValue", get_fn)
            if value:
                static_texts.append(str(value))

        # Recurse into groups and other containers
        if role in ("AXGroup", "AXScrollArea", "AXSplitGroup",
                    "AXWindow", "AXApplication", "AXWebArea"):
            title, text = _find_info_view(child, get_fn, depth + 1)
            if title or text:
                return title, text

    # Heuristic: Info View has a short title followed by a longer description
    # Look for a pair where the second is substantially longer than the first
    for i in range(len(static_texts) - 1):
        t1, t2 = static_texts[i], static_texts[i + 1]
        if len(t1) < 60 and len(t2) > len(t1) * 1.5 and len(t2) > 20:
            return t1, t2

    return None, None
