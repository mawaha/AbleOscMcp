# AbleOscMcp

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants full control of [Ableton Live](https://www.ableton.com/) via [AbletonOSC](https://github.com/ideoforms/AbletonOSC).

Control transport, create and edit MIDI clips, manipulate tracks and devices, and subscribe to real-time property changes — all from Claude Desktop, Cursor, or any other MCP client.

## Prerequisites

- **Ableton Live** 10 or later
- **AbletonOSC** installed as a Remote Script ([setup guide below](#abletonosc-setup))
- **Python 3.11+** (via [uv](https://docs.astral.sh/uv/) recommended)

## Installation

```bash
# Install with uv (recommended)
uvx ableosc-mcp

# Or install with pip
pip install ableosc-mcp
```

## AbletonOSC Setup

AbletonOSC is a free Remote Script that runs inside Ableton Live and exposes its Python API over OSC/UDP.

1. Download the latest release from [ideoforms/AbletonOSC](https://github.com/ideoforms/AbletonOSC/releases)
2. Copy the `AbletonOSC` folder to your Ableton User Library:
   - **macOS:** `~/Music/Ableton/User Library/Remote Scripts/`
   - **Windows:** `C:\Users\<name>\Documents\Ableton\User Library\Remote Scripts\`
3. Fully quit and relaunch Ableton Live
4. In Ableton: **Preferences → Link, Tempo & MIDI → Control Surface** → select `AbletonOSC`

AbletonOSC listens on UDP port **11000** and replies on port **11001**.

## Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ableton": {
      "command": "uvx",
      "args": ["ableosc-mcp"]
    }
  }
}
```

Or if you've cloned the repo:

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

## Available Tools

### Song / Transport

| Tool | Description |
|------|-------------|
| `get_session_info` | Tempo, time signature, playback state, loop settings, track/scene counts |
| `set_tempo` | Set BPM (20–999) |
| `start_playing` | Start global transport |
| `stop_playing` | Stop global transport |
| `stop_all_clips` | Stop all playing clips |
| `tap_tempo` | Send a tap-tempo pulse |
| `undo` / `redo` | Undo/redo last action |
| `set_loop` | Configure loop start, length, and enabled state |
| `get_cue_points` | List all cue points |
| `jump_to_cue` | Jump to a cue point by name or index |
| `capture_scene` | Capture playing clips into a new scene |
| `trigger_session_record` | Toggle session record mode |

### Tracks

| Tool | Description |
|------|-------------|
| `get_tracks` | List all tracks (index, name) |
| `get_track` | Full track detail: volume, pan, mute, solo, arm, devices, clips |
| `set_track_volume` | 0.0 = silent, 0.85 = unity (0 dB), 1.0 = +6 dB |
| `set_track_pan` | −1.0 = full left, 0.0 = centre, 1.0 = full right |
| `set_track_mute` / `set_track_solo` / `set_track_arm` | Toggle track states |
| `set_track_name` | Rename a track |
| `set_track_send` | Set a send level (0.0–1.0) |
| `create_midi_track` / `create_audio_track` / `create_return_track` | Add tracks |
| `delete_track` | Delete a track |
| `duplicate_track` | Duplicate a track |
| `stop_track_clips` | Stop all clips on a track |

### Clips

| Tool | Description |
|------|-------------|
| `create_clip` | Create a new empty MIDI clip in a slot |
| `delete_clip` | Delete a clip |
| `get_clip_info` | Name, length, loop settings, playing state |
| `fire_clip` / `stop_clip` | Launch or stop a clip |
| `set_clip_name` | Rename a clip |
| `set_clip_loop` | Configure clip loop start/end |
| `get_notes` | Get all MIDI notes as `{pitch, start_time, duration, velocity, mute}` |
| `add_notes` | Add MIDI notes to a clip |
| `remove_notes` | Remove notes by pitch/time range, or all notes |
| `duplicate_clip_loop` | Double loop length by duplicating contents |

### Devices

| Tool | Description |
|------|-------------|
| `get_devices` | List devices on a track |
| `get_device_parameters` | All parameters: names, values, min/max ranges |
| `get_device_parameter` | Single parameter value and display string |
| `set_device_parameter` | Set a parameter value |

### Scenes

| Tool | Description |
|------|-------------|
| `get_scenes` | List all scenes |
| `get_scene` | Scene detail: name, tempo override |
| `fire_scene` / `fire_selected_scene` | Launch a scene |
| `create_scene` / `delete_scene` / `duplicate_scene` | Manage scenes |
| `set_scene_name` | Rename a scene |
| `set_scene_tempo` | Set per-scene tempo override |

### View / Selection

| Tool | Description |
|------|-------------|
| `get_selected_track` / `set_selected_track` | Selected track in Live's UI |
| `get_selected_scene` / `set_selected_scene` | Selected scene in Live's UI |
| `get_selected_clip` / `set_selected_clip` | Selected clip slot in Live's UI |
| `get_selected_device` / `set_selected_device` | Selected device in Live's UI |

### Real-Time Listeners

Subscribe to Live property changes and poll for updates — no polling loop needed.

| Tool | Description |
|------|-------------|
| `subscribe` | Start listening to a property. Returns `sub_id` immediately; AbletonOSC sends the current value right away |
| `poll` | Collect queued events. Blocks up to `timeout_seconds` if the queue is empty |
| `unsubscribe` | Stop a listener and clean up |
| `list_subscriptions` | List active subscriptions and their queue depths |

**Example — watch tempo changes:**

```
subscribe("tempo", level="song")
→ {"sub_id": "sub_3607efaa", "status": "subscribed"}

# AbletonOSC immediately sends current value:
poll("sub_3607efaa", timeout_seconds=0)
→ {"events": [{"value": 120}]}

# Change tempo in Ableton, then:
poll("sub_3607efaa", timeout_seconds=10)
→ {"events": [{"value": 128}]}

unsubscribe("sub_3607efaa")
```

**Properties you can listen to:**

| Level | `level=` | Required index args | Useful properties |
|-------|----------|--------------------|--------------------|
| Song | `"song"` | none | `tempo`, `is_playing`, `loop`, `groove_amount` |
| Track | `"track"` | `track_index` | `mute`, `solo`, `arm`, `volume`, `panning`, `output_meter_level` |
| Clip | `"clip"` | `track_index`, `clip_index` | `is_playing`, `is_recording`, `playing_position` |
| Clip slot | `"clip_slot"` | `track_index`, `clip_index` | `has_clip`, `is_playing`, `is_triggered` |
| Scene | `"scene"` | `scene_index` | `name` |
| Device | `"device"` | `track_index`, `device_index` | `name` |
| View | `"view"` | none | `selected_track`, `selected_scene` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ABLEOSC_HOST` | `127.0.0.1` | AbletonOSC host |
| `ABLEOSC_SEND_PORT` | `11000` | Port AbletonOSC listens on |
| `ABLEOSC_RECEIVE_PORT` | `11001` | Port we listen on for responses |

## Development

```bash
git clone https://github.com/mawaha/AbleOscMcp
cd AbleOscMcp
uv sync --all-extras

# Unit tests (no Ableton needed)
uv run pytest tests/unit/ -v

# Integration tests (requires Ableton Live + AbletonOSC running)
# Kill any running ableosc-mcp server first to free port 11001
lsof -ti :11001 | xargs kill
ABLEOSC_INTEGRATION=1 uv run pytest tests/integration/ -v

# Coverage report
uv run pytest tests/unit/ --cov --cov-report=term-missing
```

## Architecture

```
AI client (Claude Desktop, Cursor, etc.)
    │  MCP / stdio
    ▼
src/ableosc/server.py        ← FastMCP server, tool registration
    │  asyncio + python-osc / UDP
    ▼
AbletonOSC Remote Script     ← installed in Ableton Live
(inside Ableton Live)
    │  Live Python API
    ▼
Ableton Live
```

Unlike other Ableton MCP integrations that implement a custom protocol, this project wraps [AbletonOSC](https://github.com/ideoforms/AbletonOSC) — a mature, well-tested Remote Script with a comprehensive API surface including real-time event listeners.

## License

MIT — see [LICENSE](LICENSE).
