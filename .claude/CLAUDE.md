# AbleOscMcp — Project Instructions

> **Keep this file up to date.** Update after significant changes to architecture, patterns, or APIs.

## Overview

An MCP (Model Context Protocol) server that exposes Ableton Live's full API to AI assistants
via [AbletonOSC](https://github.com/ideoforms/AbletonOSC). Unlike other Ableton MCP projects
that use a custom JSON/TCP protocol, this project wraps the mature AbletonOSC layer, giving
us access to real-time event listeners, comprehensive device parameter control, and the full
OSC API surface.

## Architecture

```
AI client (Claude Desktop, Cursor, etc.)
    │  MCP / stdio
    ▼
src/ableosc/server.py         ← FastMCP server, tool registration
    │  asyncio + python-osc / UDP
    ▼
AbletonOSC Remote Script      ← must be installed in Ableton Live
(inside Ableton Live)
    │  Live Python API
    ▼
Ableton Live
```

## Key Files

| File | Purpose |
|------|---------|
| `src/ableosc/client.py` | OSC client: request/response, listeners, ping |
| `src/ableosc/server.py` | FastMCP server factory + `main()` entry point |
| `src/ableosc/tools/song.py` | Transport, tempo, loop, undo, cue points |
| `src/ableosc/tools/track.py` | Track CRUD, volume, pan, mute, solo, arm |
| `src/ableosc/tools/clip.py` | Clip creation, MIDI notes, loop settings |
| `src/ableosc/tools/device.py` | Device parameter inspection and control |
| `src/ableosc/tools/scene.py` | Scene launch, creation, tempo overrides |
| `src/ableosc/tools/view.py` | Live UI selection (selected track/clip/device) |
| `tests/conftest.py` | `MockOscClient`, `MockAbletonOscServer`, fixtures |

## Development Workflow

```bash
# Install with uv (creates .venv automatically)
uv sync --all-extras

# Run unit tests (no Ableton needed)
uv run pytest tests/unit/ -v

# Run all tests including OscClient network tests
uv run pytest tests/ -v --ignore=tests/integration

# Run integration tests (requires Ableton Live + AbletonOSC)
ABLEOSC_INTEGRATION=1 uv run pytest tests/integration/ -v

# Run coverage report
uv run pytest tests/unit/ --cov --cov-report=term-missing

# Run the MCP server
uv run ableosc-mcp
```

## AbletonOSC Setup

1. Download `AbletonOSC` from https://github.com/ideoforms/AbletonOSC
2. Copy the `AbletonOSC` folder to:
   - macOS: `~/Library/Preferences/Ableton/Live x.y.z/User Remote Scripts/`
   - Windows: `C:\Users\<name>\AppData\Roaming\Ableton\Live x.y.z\User Remote Scripts\`
3. In Ableton: Preferences → Link/Tempo/MIDI → Control Surface → `AbletonOSC`
4. AbletonOSC listens on UDP port 11000, replies on port 11001 (both configurable via env vars)

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "ableton": {
      "command": "uv",
      "args": ["run", "ableosc-mcp"],
      "cwd": "/path/to/AbleOscMcp"
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ABLEOSC_HOST` | `127.0.0.1` | AbletonOSC host |
| `ABLEOSC_SEND_PORT` | `11000` | Port AbletonOSC listens on |
| `ABLEOSC_RECEIVE_PORT` | `11001` | Port we listen on for responses |

## Design Principles

1. **Wrap, don't reimplement** — AbletonOSC handles all Ableton-side complexity. We provide
   the MCP layer on top.
2. **Tools are pure functions** — Each tool module contains plain `async def fn(client, ...)`.
   The MCP registration in `server.py` is a thin closure layer. Test the pure functions, not
   the MCP wrappers.
3. **Testable without Ableton** — `MockOscClient` enables unit testing of all business logic.
   `MockAbletonOscServer` enables network-level testing of `OscClient`. Real Ableton only
   needed for integration tests.
4. **Fail loudly** — Validate inputs (tempo range, volume range, etc.) and raise `ValueError`
   with clear messages. Let exceptions propagate through FastMCP rather than swallowing them.
5. **Response parsing is defensive** — `_scalar()` handles both single-value and
   `(index, value)` response formats. Test with real AbletonOSC to verify actual format.

## Adding New Tools

1. Add a function to the appropriate `src/ableosc/tools/*.py` module
2. Register it in `server.py` as a `@mcp.tool()` closure
3. Write unit tests in `tests/unit/test_<module>_tools.py`
4. Verify against real AbletonOSC (integration test or manual)

## OSC Protocol Notes

- GET: `send(address, *args)` + `get(address, *args)` → waits for response on same address
- SET/ACTION: `send(address, *args)` → fire-and-forget
- LISTEN: `send("/live/*/start_listen/prop")` → AbletonOSC sends updates on GET address
- Booleans: OSC uses int 0/1 — convert with `bool(args[0])` when parsing responses
- Track responses: may include track_index as first arg — handled by `_scalar()` helper
