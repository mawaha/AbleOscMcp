"""AbleOscMcp — MCP server entry point.

Registers all MCP tools and resources, connects to AbletonOSC, and runs
the FastMCP stdio server for use with Claude Desktop, Cursor, or any other
MCP client.

Architecture:
    MCP client (stdio)
        ↕  MCP protocol
    this server
        ↕  OSC / UDP
    AbletonOSC Remote Script (inside Ableton Live)
        ↕  Live Python API
    Ableton Live
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server.fastmcp import FastMCP

from ableosc.client import OscClient
from ableosc.tools import clip as clip_tools
from ableosc.tools import device as device_tools
from ableosc.tools import scene as scene_tools
from ableosc.tools import song as song_tools
from ableosc.tools import track as track_tools
from ableosc.tools import view as view_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server factory — separated from main() so tests can inject a mock client
# ---------------------------------------------------------------------------


def create_server(client: OscClient) -> FastMCP:
    """Create and configure the FastMCP server with all tools registered.

    Args:
        client: An initialised OscClient (or mock) to use for all tool calls.

    Returns:
        Configured FastMCP instance ready to run.
    """
    mcp = FastMCP("AbleOscMcp")

    # ------------------------------------------------------------------
    # Resources — expose live session state as queryable data
    # ------------------------------------------------------------------

    @mcp.resource("session://state")
    async def session_state() -> str:
        """Live snapshot of the current Ableton session."""
        info = await song_tools.get_session_info(client)
        tracks = await track_tools.get_tracks(client)
        info["tracks"] = tracks["tracks"]
        return json.dumps(info, indent=2)

    # ------------------------------------------------------------------
    # Song tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_session_info() -> dict[str, Any]:
        """Get current Ableton session state: tempo, time signature, playback status,
        loop settings, track and scene counts."""
        return await song_tools.get_session_info(client)

    @mcp.tool()
    async def set_tempo(tempo: float) -> dict[str, Any]:
        """Set the session tempo in BPM (20–999)."""
        return await song_tools.set_tempo(client, tempo)

    @mcp.tool()
    async def start_playing() -> dict[str, str]:
        """Start global transport playback."""
        return await song_tools.start_playing(client)

    @mcp.tool()
    async def stop_playing() -> dict[str, str]:
        """Stop global transport playback."""
        return await song_tools.stop_playing(client)

    @mcp.tool()
    async def stop_all_clips() -> dict[str, str]:
        """Stop all currently playing clips across the entire session."""
        return await song_tools.stop_all_clips(client)

    @mcp.tool()
    async def tap_tempo() -> dict[str, str]:
        """Send a tap-tempo pulse. Call repeatedly to set tempo by tapping."""
        return await song_tools.tap_tempo(client)

    @mcp.tool()
    async def undo() -> dict[str, str]:
        """Undo the last action in Ableton Live."""
        return await song_tools.undo(client)

    @mcp.tool()
    async def redo() -> dict[str, str]:
        """Redo the last undone action in Ableton Live."""
        return await song_tools.redo(client)

    @mcp.tool()
    async def set_loop(
        enabled: bool,
        start_beats: float | None = None,
        length_beats: float | None = None,
    ) -> dict[str, Any]:
        """Enable/disable the session loop and optionally set its start and length in beats."""
        return await song_tools.set_loop(client, enabled, start_beats, length_beats)

    @mcp.tool()
    async def get_cue_points() -> dict[str, Any]:
        """Get all cue points defined in the session."""
        return await song_tools.get_cue_points(client)

    @mcp.tool()
    async def jump_to_cue(name_or_index: str) -> dict[str, str]:
        """Jump playback position to a cue point. Accepts cue name (str) or index (int as str)."""
        try:
            arg: str | int = int(name_or_index)
        except ValueError:
            arg = name_or_index
        return await song_tools.jump_to_cue(client, arg)

    @mcp.tool()
    async def capture_scene() -> dict[str, str]:
        """Capture all currently playing clips into a new scene."""
        return await song_tools.capture_scene(client)

    @mcp.tool()
    async def trigger_session_record() -> dict[str, str]:
        """Toggle session record mode."""
        return await song_tools.trigger_session_record(client)

    # ------------------------------------------------------------------
    # Track tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_tracks() -> dict[str, Any]:
        """Get a summary list of all tracks: index, name."""
        return await track_tools.get_tracks(client)

    @mcp.tool()
    async def get_track(track_index: int) -> dict[str, Any]:
        """Get detailed info for one track: name, volume, pan, mute, solo, arm,
        devices, clips."""
        return await track_tools.get_track(client, track_index)

    @mcp.tool()
    async def set_track_volume(track_index: int, volume: float) -> dict[str, Any]:
        """Set track volume. 0.0 = silent, 0.85 = unity gain (0dB), 1.0 = +6dB."""
        return await track_tools.set_track_volume(client, track_index, volume)

    @mcp.tool()
    async def set_track_pan(track_index: int, pan: float) -> dict[str, Any]:
        """Set track panning. -1.0 = full left, 0.0 = centre, 1.0 = full right."""
        return await track_tools.set_track_pan(client, track_index, pan)

    @mcp.tool()
    async def set_track_mute(track_index: int, mute: bool) -> dict[str, Any]:
        """Mute (True) or unmute (False) a track."""
        return await track_tools.set_track_mute(client, track_index, mute)

    @mcp.tool()
    async def set_track_solo(track_index: int, solo: bool) -> dict[str, Any]:
        """Solo (True) or un-solo (False) a track."""
        return await track_tools.set_track_solo(client, track_index, solo)

    @mcp.tool()
    async def set_track_arm(track_index: int, arm: bool) -> dict[str, Any]:
        """Arm (True) or disarm (False) a track for recording."""
        return await track_tools.set_track_arm(client, track_index, arm)

    @mcp.tool()
    async def set_track_name(track_index: int, name: str) -> dict[str, Any]:
        """Rename a track."""
        return await track_tools.set_track_name(client, track_index, name)

    @mcp.tool()
    async def set_track_send(
        track_index: int, send_index: int, value: float
    ) -> dict[str, Any]:
        """Set a send level for a track (0.0–1.0). send_index 0 = first return track."""
        return await track_tools.set_track_send(client, track_index, send_index, value)

    @mcp.tool()
    async def create_midi_track() -> dict[str, str]:
        """Create a new MIDI track at the end of the session."""
        return await track_tools.create_midi_track(client)

    @mcp.tool()
    async def create_audio_track() -> dict[str, str]:
        """Create a new audio track at the end of the session."""
        return await track_tools.create_audio_track(client)

    @mcp.tool()
    async def create_return_track() -> dict[str, str]:
        """Create a new return track."""
        return await track_tools.create_return_track(client)

    @mcp.tool()
    async def delete_track(track_index: int) -> dict[str, Any]:
        """Delete a track. Use with caution — this cannot be undone via the MCP server."""
        return await track_tools.delete_track(client, track_index)

    @mcp.tool()
    async def stop_track_clips(track_index: int) -> dict[str, Any]:
        """Stop all playing clips on a specific track."""
        return await track_tools.stop_track_clips(client, track_index)

    @mcp.tool()
    async def duplicate_track(track_index: int) -> dict[str, Any]:
        """Duplicate a track."""
        return await track_tools.duplicate_track(client, track_index)

    # ------------------------------------------------------------------
    # Clip tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_clip_info(track_index: int, clip_index: int) -> dict[str, Any]:
        """Get metadata for a clip: name, length, loop settings, playing state."""
        return await clip_tools.get_clip_info(client, track_index, clip_index)

    @mcp.tool()
    async def create_clip(
        track_index: int, clip_index: int, length_beats: float = 4.0
    ) -> dict[str, Any]:
        """Create a new empty MIDI clip in the given slot."""
        return await clip_tools.create_clip(client, track_index, clip_index, length_beats)

    @mcp.tool()
    async def delete_clip(track_index: int, clip_index: int) -> dict[str, Any]:
        """Delete a clip from a clip slot."""
        return await clip_tools.delete_clip(client, track_index, clip_index)

    @mcp.tool()
    async def fire_clip(track_index: int, clip_index: int) -> dict[str, Any]:
        """Launch a clip slot."""
        return await clip_tools.fire_clip(client, track_index, clip_index)

    @mcp.tool()
    async def stop_clip(track_index: int, clip_index: int) -> dict[str, Any]:
        """Stop a clip slot."""
        return await clip_tools.stop_clip(client, track_index, clip_index)

    @mcp.tool()
    async def set_clip_name(
        track_index: int, clip_index: int, name: str
    ) -> dict[str, Any]:
        """Rename a clip."""
        return await clip_tools.set_clip_name(client, track_index, clip_index, name)

    @mcp.tool()
    async def set_clip_loop(
        track_index: int,
        clip_index: int,
        looping: bool,
        loop_start: float | None = None,
        loop_end: float | None = None,
    ) -> dict[str, Any]:
        """Configure loop settings for a clip."""
        return await clip_tools.set_clip_loop(
            client, track_index, clip_index, looping, loop_start, loop_end
        )

    @mcp.tool()
    async def get_notes(track_index: int, clip_index: int) -> dict[str, Any]:
        """Get all MIDI notes from a clip as a list of
        {pitch, start_time, duration, velocity, mute} dicts."""
        return await clip_tools.get_notes(client, track_index, clip_index)

    @mcp.tool()
    async def add_notes(
        track_index: int,
        clip_index: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Add MIDI notes to a clip. Existing notes are preserved.

        Each note: {"pitch": 60, "start_time": 0.0, "duration": 0.25,
                    "velocity": 100, "mute": 0}
        pitch: MIDI note number 0-127 (60 = middle C)
        start_time: offset from clip start in beats
        duration: note length in beats
        velocity: MIDI velocity 0-127
        mute: 0 = audible, 1 = muted
        """
        return await clip_tools.add_notes(client, track_index, clip_index, notes)

    @mcp.tool()
    async def remove_notes(
        track_index: int,
        clip_index: int,
        pitch_start: int | None = None,
        pitch_span: int | None = None,
        time_start: float | None = None,
        time_span: float | None = None,
    ) -> dict[str, Any]:
        """Remove MIDI notes from a clip. Without arguments, removes all notes.
        Use pitch_start/span and time_start/span to target a range."""
        return await clip_tools.remove_notes(
            client, track_index, clip_index, pitch_start, pitch_span, time_start, time_span
        )

    @mcp.tool()
    async def duplicate_clip_loop(
        track_index: int, clip_index: int
    ) -> dict[str, Any]:
        """Double a clip's loop length by duplicating its contents."""
        return await clip_tools.duplicate_clip_loop(client, track_index, clip_index)

    # ------------------------------------------------------------------
    # Device tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_devices(track_index: int) -> dict[str, Any]:
        """List all devices on a track with index, name, type, and class name."""
        return await device_tools.get_devices(client, track_index)

    @mcp.tool()
    async def get_device_parameters(
        track_index: int, device_index: int
    ) -> dict[str, Any]:
        """Get all parameters for a device: names, values, and min/max ranges."""
        return await device_tools.get_device_parameters(client, track_index, device_index)

    @mcp.tool()
    async def get_device_parameter(
        track_index: int, device_index: int, param_index: int
    ) -> dict[str, Any]:
        """Get the current value and display string for a single device parameter."""
        return await device_tools.get_device_parameter(
            client, track_index, device_index, param_index
        )

    @mcp.tool()
    async def set_device_parameter(
        track_index: int, device_index: int, param_index: int, value: float
    ) -> dict[str, Any]:
        """Set a device parameter. Use get_device_parameters to discover valid ranges."""
        return await device_tools.set_device_parameter(
            client, track_index, device_index, param_index, value
        )

    # ------------------------------------------------------------------
    # Scene tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_scenes() -> dict[str, Any]:
        """Get all scenes: index and name."""
        return await scene_tools.get_scenes(client)

    @mcp.tool()
    async def get_scene(scene_index: int) -> dict[str, Any]:
        """Get detailed info for one scene: name, tempo override."""
        return await scene_tools.get_scene(client, scene_index)

    @mcp.tool()
    async def fire_scene(scene_index: int) -> dict[str, Any]:
        """Launch all clips in a scene."""
        return await scene_tools.fire_scene(client, scene_index)

    @mcp.tool()
    async def create_scene() -> dict[str, str]:
        """Create a new empty scene."""
        return await scene_tools.create_scene(client)

    @mcp.tool()
    async def delete_scene(scene_index: int) -> dict[str, Any]:
        """Delete a scene."""
        return await scene_tools.delete_scene(client, scene_index)

    @mcp.tool()
    async def duplicate_scene(scene_index: int) -> dict[str, Any]:
        """Duplicate a scene."""
        return await scene_tools.duplicate_scene(client, scene_index)

    @mcp.tool()
    async def set_scene_name(scene_index: int, name: str) -> dict[str, Any]:
        """Rename a scene."""
        return await scene_tools.set_scene_name(client, scene_index, name)

    @mcp.tool()
    async def set_scene_tempo(
        scene_index: int, tempo: float, enabled: bool = True
    ) -> dict[str, Any]:
        """Set a tempo override on a scene (20–999 BPM)."""
        return await scene_tools.set_scene_tempo(client, scene_index, tempo, enabled)

    @mcp.tool()
    async def fire_selected_scene() -> dict[str, str]:
        """Launch the scene that is currently selected in Live's UI."""
        return await scene_tools.fire_selected_scene(client)

    # ------------------------------------------------------------------
    # View tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_selected_track() -> dict[str, Any]:
        """Get the index of the currently selected track in Live's UI."""
        return await view_tools.get_selected_track(client)

    @mcp.tool()
    async def set_selected_track(track_index: int) -> dict[str, Any]:
        """Select a track in Live's UI."""
        return await view_tools.set_selected_track(client, track_index)

    @mcp.tool()
    async def get_selected_scene() -> dict[str, Any]:
        """Get the index of the currently selected scene in Live's UI."""
        return await view_tools.get_selected_scene(client)

    @mcp.tool()
    async def set_selected_scene(scene_index: int) -> dict[str, Any]:
        """Select a scene in Live's UI."""
        return await view_tools.set_selected_scene(client, scene_index)

    @mcp.tool()
    async def get_selected_clip() -> dict[str, Any]:
        """Get the track/clip index of the currently selected clip in Live's UI."""
        return await view_tools.get_selected_clip(client)

    @mcp.tool()
    async def set_selected_clip(track_index: int, clip_index: int) -> dict[str, Any]:
        """Select a clip slot in Live's UI."""
        return await view_tools.set_selected_clip(client, track_index, clip_index)

    @mcp.tool()
    async def get_selected_device() -> dict[str, Any]:
        """Get the track/device index of the currently selected device in Live's UI."""
        return await view_tools.get_selected_device(client)

    @mcp.tool()
    async def set_selected_device(track_index: int, device_index: int) -> dict[str, Any]:
        """Select a device in Live's UI."""
        return await view_tools.set_selected_device(client, track_index, device_index)

    return mcp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the AbleOscMcp server."""
    host = os.getenv("ABLEOSC_HOST", "127.0.0.1")
    send_port = int(os.getenv("ABLEOSC_SEND_PORT", "11000"))
    receive_port = int(os.getenv("ABLEOSC_RECEIVE_PORT", "11001"))

    async def run() -> None:
        client = OscClient(host=host, send_port=send_port, receive_port=receive_port)
        await client.start()

        try:
            alive = await client.ping()
            if alive:
                logger.info("Connected to AbletonOSC")
            else:
                logger.warning(
                    "AbletonOSC did not respond to ping. "
                    "Is Ableton Live running with the AbletonOSC Remote Script active?"
                )

            mcp = create_server(client)
            await mcp.run_stdio_async()
        finally:
            await client.stop()

    asyncio.run(run())


if __name__ == "__main__":
    main()
