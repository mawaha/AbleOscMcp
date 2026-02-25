"""
Ableton Info View reader using macOS Vision OCR.

Reads the title and description text from Ableton's Info View panel —
the same text shown when hovering over any control in Ableton Live.

Ableton uses a custom OpenGL renderer so its controls are not exposed
via the standard macOS Accessibility API. Instead, we screenshot the
bottom-left region of the Ableton window (where Info View always lives)
and run Vision OCR on it.

Requirements:
    - macOS only
    - Ableton Live must be running
    - pyobjc-framework-vision and pyobjc-framework-quartz must be installed

Usage:
    info = read_info_view()
    # {"title": "Filter Frequency", "text": "This defines the center..."}
"""

from __future__ import annotations

import re
import subprocess
import sys


def is_available() -> bool:
    """Return True if OCR-based Info View reading is available."""
    if sys.platform != "darwin":
        return False
    try:
        import Quartz  # noqa: F401
        import Vision  # noqa: F401
        return True
    except ImportError:
        return False


def read_info_view(app_name: str = "Live") -> dict[str, str] | None:
    """
    Read the current Info View title and text from Ableton Live via OCR.

    Screenshots the bottom-left region of the Ableton window (where the
    Info View panel lives) and runs macOS Vision text recognition on it.

    Returns {"title": str, "text": str} or None if unavailable/not found.

    Raises:
        RuntimeError: If not on macOS.
        ImportError: If pyobjc is not installed.
    """
    if sys.platform != "darwin":
        raise RuntimeError("Info View reading is only supported on macOS")

    try:
        import Quartz
        import Vision
        from ApplicationServices import (
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
        )
    except ImportError:
        raise ImportError(
            "pyobjc is required for Info View reading. "
            "Install with: uv sync --extra macos"
        )

    pid = _find_pid(app_name)
    if pid is None:
        return None

    frame = _get_window_frame(pid, AXUIElementCreateApplication, AXUIElementCopyAttributeValue)
    if frame is None:
        return None

    wx, wy, ww, wh = frame

    # Info View is always in the bottom-left of the Ableton window.
    # Width: ~22% of window width (excludes device controls to the right)
    # Height: ~22% of window height (tall enough to capture title + body)
    # Slight upward offset to avoid the status bar at the very bottom edge.
    info_w = ww * 0.22
    info_h = wh * 0.22
    info_x = wx
    info_y = wy + wh - info_h - (wh * 0.02)

    img = _take_screenshot(info_x, info_y, info_w, info_h, Quartz)
    if img is None:
        return None

    lines = _ocr_image(img, Vision)
    title, text = _parse_ocr_lines(lines)

    if title is None:
        return None

    return {"title": title, "text": text or ""}


# ── internal helpers ──────────────────────────────────────────────────────────


def _find_pid(app_name: str) -> int | None:
    """Find the PID of a running application by name."""
    result = subprocess.run(
        ["pgrep", "-x", app_name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        pids = result.stdout.strip().split()
        if pids:
            return int(pids[0])
    return None


def _get_window_frame(pid: int, ax_create, ax_get_attr) -> tuple[float, float, float, float] | None:
    """Return (x, y, width, height) of the main Ableton window."""
    app = ax_create(pid)

    def attr(el, name):
        err, val = ax_get_attr(el, name, None)
        return val if err == 0 else None

    window = attr(app, "AXFocusedWindow") or attr(app, "AXMainWindow")
    if window is None:
        return None

    frame = attr(window, "AXFrame")
    if frame is None:
        return None

    # AXFrame is an AXValue (kAXValueCGRectType) — parse its string repr
    m = re.search(r'x:([\d.]+)\s+y:([\d.]+)\s+w:([\d.]+)\s+h:([\d.]+)', str(frame))
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
    return None


def _take_screenshot(x: float, y: float, w: float, h: float, Quartz) -> object | None:
    """Take a screenshot of the given screen region. Returns a CGImage or None."""
    rect = Quartz.CGRectMake(x, y, w, h)
    img = Quartz.CGWindowListCreateImage(
        rect,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault,
    )
    return img


def _ocr_image(cg_image, Vision) -> list[str]:
    """Run Vision text recognition on a CGImage. Returns list of text lines."""
    results = []

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
        cg_image, {}
    )

    def completion(request, error):
        if error:
            return
        for obs in request.results() or []:
            candidates = obs.topCandidates_(1)
            if candidates:
                results.append(str(candidates[0].string()))

    request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(completion)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)
    handler.performRequests_error_([request], None)
    return results


def _parse_ocr_lines(lines: list[str]) -> tuple[str | None, str | None]:
    """
    Extract Info View title and body text from raw OCR observations.

    Ableton's Info View renders as:
        line 0:     title  (e.g. "Filter Frequency")
        lines 1-N:  body text  (natural language description)
        lines N+1+: UI control labels  ("Operator W", "Coarse", "Fine", ...)

    The split between body and UI labels is the first line that matches
    the "Operator" header — Ableton always renders the device name header
    as the first UI element below the Info View panel in this region.
    """
    if not lines:
        return None, None

    title = lines[0].strip()
    if not title:
        return None, None

    # Find where the UI control labels begin
    body_lines = []
    for line in lines[1:]:
        if _is_ui_section_start(line):
            break
        body_lines.append(line.strip())

    body = " ".join(body_lines).strip()
    return title, body


def _is_ui_section_start(line: str) -> bool:
    """
    Return True if this line is the start of the Ableton UI control section
    (rather than Info View description text).

    The device header "Operator W" (or "• Operator W") always appears as the
    first UI element below the Info View text in our captured region.
    """
    stripped = line.strip().lstrip("•").strip()
    return stripped.lower().startswith("operator")
