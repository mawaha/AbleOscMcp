# Integration Tests

These tests require a running Ableton Live instance with AbletonOSC installed
and active as a Control Surface.

## Prerequisites

1. Install [AbletonOSC](https://github.com/ideoforms/AbletonOSC):
   - Download the `AbletonOSC` folder from the releases page
   - Copy it to your Ableton Remote Scripts directory:
     - macOS: `~/Library/Preferences/Ableton/Live x.y.z/User Remote Scripts/`
     - Windows: `C:\Users\<name>\AppData\Roaming\Ableton\Live x.y.z\User Remote Scripts\`
   - In Ableton: Preferences → Link/Tempo/MIDI → Control Surface → select `AbletonOSC`

2. Open a Live session with some tracks.

## Running

```bash
ABLEOSC_INTEGRATION=1 uv run pytest tests/integration/ -v -m integration
```

Without the `ABLEOSC_INTEGRATION=1` env var, integration tests are skipped.

## What integration tests cover

- Real OSC round-trip: verify AbletonOSC response formats match our parsing
- End-to-end tool calls against a live session
- Listener / real-time event delivery
- Error handling when requesting invalid indices
