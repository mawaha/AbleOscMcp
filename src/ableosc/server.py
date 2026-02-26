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

from ableosc import resources
from ableosc.client import OscClient
from ableosc.device_database import DeviceDatabase
from ableosc.subscriptions import SubscriptionRegistry
from ableosc.tools import clip as clip_tools
from ableosc.tools import device as device_tools
from ableosc.tools import device_db as device_db_tools
from ableosc.tools import listen as listen_tools
from ableosc.tools import music as music_tools
from ableosc.tools import scene as scene_tools
from ableosc.tools import song as song_tools
from ableosc.tools import browser_tools
from ableosc.tools import rack as rack_tools
from ableosc.tools import track as track_tools
from ableosc.tools import view as view_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server factory — separated from main() so tests can inject a mock client
# ---------------------------------------------------------------------------


def create_server(client: OscClient, rack_client: OscClient | None = None) -> FastMCP:
    """Create and configure the FastMCP server with all tools registered.

    Args:
        client: An initialised OscClient (or mock) to use for all tool calls.

    Returns:
        Configured FastMCP instance ready to run.
    """
    mcp = FastMCP("AbleOscMcp")
    registry = SubscriptionRegistry()
    db = DeviceDatabase()

    # ------------------------------------------------------------------
    # Resources — expose live session state as queryable data
    # ------------------------------------------------------------------

    @mcp.resource("session://state")
    async def session_state() -> str:
        """Live snapshot of the current Ableton session."""
        data = await resources.session_state(client)
        return json.dumps(data, indent=2)

    @mcp.resource("session://tracks")
    async def session_tracks_resource() -> str:
        """Full detail for all tracks: name, volume, pan, mute, solo, arm, devices, clips."""
        data = await resources.session_tracks(client)
        return json.dumps(data, indent=2)

    @mcp.resource("session://device/{track_index}/{device_index}")
    async def session_device_resource(track_index: int, device_index: int) -> str:
        """All parameters for a device: name, value, min, max, display string."""
        data = await resources.device_resource(client, track_index, device_index)
        return json.dumps(data, indent=2)

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

    @mcp.tool()
    async def save_project() -> dict[str, Any]:
        """Save the current Ableton project to disk (macOS).

        Sends Cmd+S to Ableton Live via system automation. If a Save dialog
        appears (new project), you will need to confirm the filename.
        """
        return await song_tools.save_project()

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
        """Get metadata for a clip: name, length, loop settings, playing state.
        Returns {"has_clip": false} if the slot is empty."""
        return await clip_tools.get_clip_info(client, track_index, clip_index)

    @mcp.tool()
    async def get_clip_slots(track_index: int) -> dict[str, Any]:
        """Return occupancy status for every clip slot on a track.

        Returns a list of {"slot_index": N, "has_clip": bool} entries — one per scene.
        Use this before creating clips to avoid overwriting existing content."""
        return await clip_tools.get_clip_slots(client, track_index)

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

    # ------------------------------------------------------------------
    # Musical intelligence tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def generate_chord(
        root: str,
        quality: str = "major",
        octave: int = 4,
        voicing: str = "close",
    ) -> dict[str, Any]:
        """Generate MIDI pitches for a chord.

        root: Note name e.g. "C", "F#", "Bb"
        quality: Chord quality e.g. "major", "minor", "m7", "maj7", "dim7", "7", "sus4"
        octave: Octave for the root. 4 = middle octave (C4 = MIDI 60)
        voicing: "close" (default) or "open" (spread across two octaves)

        Returns pitches list, note names, and chord metadata.
        """
        return await music_tools.generate_chord(root, quality, octave, voicing)

    @mcp.tool()
    async def add_notes_in_scale(
        track_index: int,
        clip_index: int,
        notes: list[dict[str, Any]],
        scale_root: str,
        scale_name: str,
    ) -> dict[str, Any]:
        """Add MIDI notes to a clip, snapping each pitch to the nearest scale tone first.

        Prevents out-of-scale notes — useful when generating melodies or harmonies.

        scale_root: Root note e.g. "C", "F#", "Bb"
        scale_name: e.g. "major", "minor", "dorian", "pentatonic_minor", "blues"

        Each note: {"pitch": 60, "start_time": 0.0, "duration": 0.25, "velocity": 100, "mute": 0}
        """
        return await music_tools.add_notes_in_scale(
            client, track_index, clip_index, notes, scale_root, scale_name
        )

    @mcp.tool()
    async def transpose_clip(
        track_index: int,
        clip_index: int,
        semitones: int,
    ) -> dict[str, Any]:
        """Transpose all notes in a clip by a number of semitones.

        Positive = up, negative = down. Notes shifted out of MIDI range (0–127) are dropped.
        """
        return await music_tools.transpose_clip(client, track_index, clip_index, semitones)

    @mcp.tool()
    async def quantize_clip(
        track_index: int,
        clip_index: int,
        grid: float = 0.25,
        amount: float = 1.0,
    ) -> dict[str, Any]:
        """Snap note start times in a clip to a rhythmic grid.

        grid: Grid size in beats. 0.25 = 1/16 note, 0.5 = 1/8, 1.0 = 1/4 (quarter note)
        amount: Quantize strength 0.0–1.0 (default 1.0 = full snap, 0.5 = halfway)
        """
        return await music_tools.quantize_clip(client, track_index, clip_index, grid, amount)

    @mcp.tool()
    async def humanize_clip(
        track_index: int,
        clip_index: int,
        timing_amount: float = 0.02,
        velocity_amount: int = 10,
    ) -> dict[str, Any]:
        """Add subtle random timing and velocity variation to notes in a clip.

        Makes programmed patterns feel more human and less mechanical.

        timing_amount: Max timing offset in beats (default 0.02 ≈ 5ms at 120BPM)
        velocity_amount: Max velocity offset ± (default 10)
        """
        return await music_tools.humanize_clip(
            client, track_index, clip_index, timing_amount, velocity_amount
        )

    # ------------------------------------------------------------------
    # Device parameter database tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def catalog_device(
        track_index: int,
        device_index: int,
    ) -> dict[str, Any]:
        """Scan a device's parameters and save them to the local database.

        Run this once per device to enable lookup_parameter and set_device_parameter_by_name.
        The database persists at ~/.ableosc/device_db.json between sessions.
        """
        return await device_db_tools.catalog_device(client, db, track_index, device_index)

    @mcp.tool()
    async def list_known_devices() -> dict[str, Any]:
        """List all devices currently in the local parameter database."""
        return await device_db_tools.list_known_devices(db)

    @mcp.tool()
    async def lookup_parameter(
        device_name: str,
        param_name: str,
    ) -> dict[str, Any]:
        """Search for a device parameter by name using fuzzy matching.

        Requires the device to have been catalogued with catalog_device first.
        Returns all matching parameters sorted by match quality (exact → contains).

        device_name: e.g. "Operator", "Wavetable", "Auto Filter"
        param_name: Full or partial parameter name e.g. "filter cutoff", "cutoff", "attack"
        """
        return await device_db_tools.lookup_parameter(db, device_name, param_name)

    @mcp.tool()
    async def annotate_parameter(
        device_name: str,
        param_name: str,
        info_title: str,
        info_text: str,
    ) -> dict[str, Any]:
        """Add or update the Info View title and description for a device parameter.

        Use this to store the text shown in Ableton's Info View panel alongside
        the parameter in the local database. Hover over a control in Ableton,
        read what the Info View says, then call this to persist it.

        device_name: Device name as catalogued e.g. "Operator"
        param_name: Parameter name (exact or partial) e.g. "Filter Freq"
        info_title: Info View title e.g. "Filter Frequency"
        info_text: Info View body text e.g. "This defines the center or cutoff frequency..."
        """
        return await device_db_tools.annotate_parameter(
            db, device_name, param_name, info_title, info_text
        )

    @mcp.tool()
    async def read_info_view() -> dict[str, Any]:
        """Read the current Info View title and text from Ableton Live's UI.

        Uses the macOS Accessibility API to capture whatever text Ableton is
        currently showing in its Info View panel (bottom-left of the screen).

        Hover over any control in Ableton first, then call this tool to capture
        its description. Combine with annotate_parameter to store it in the database.

        Requires Accessibility access: System Settings → Privacy & Security → Accessibility
        → enable Terminal (or whichever app is running the MCP server).
        """
        return await device_db_tools.read_info_view()

    @mcp.tool()
    async def set_device_parameter_by_name(
        track_index: int,
        device_index: int,
        device_name: str,
        param_name: str,
        value: float,
    ) -> dict[str, Any]:
        """Look up a parameter by name and set it in one step.

        Combines lookup_parameter + set_device_parameter.
        Requires the device to have been catalogued with catalog_device first.

        device_name: e.g. "Operator", "Wavetable"
        param_name: Full or partial parameter name e.g. "filter cutoff"
        value: Value to set (checked against min/max in the database entry)
        """
        return await device_db_tools.set_device_parameter_by_name(
            client, db, track_index, device_index, device_name, param_name, value
        )

    # ------------------------------------------------------------------
    # Listener tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def subscribe(
        prop: str,
        level: str = "song",
        track_index: int | None = None,
        clip_index: int | None = None,
        scene_index: int | None = None,
        device_index: int | None = None,
    ) -> dict[str, Any]:
        """Start listening to a Live property. Returns a sub_id immediately.
        AbletonOSC sends the current value on subscribe, so poll() will have
        at least one event right away.

        level: "song" | "track" | "clip" | "clip_slot" | "scene" | "device" | "view"

        Index args required per level:
            track      → track_index
            scene      → scene_index
            clip/slot  → track_index + clip_index
            device     → track_index + device_index
            song/view  → none

        Example properties:
            song:   tempo, is_playing, loop, groove_amount
            track:  mute, solo, arm, volume, panning, output_meter_level
            clip:   is_playing, is_recording, playing_position
            view:   selected_track, selected_scene
        """
        return await listen_tools.subscribe(
            client, registry, prop, level,
            track_index, clip_index, scene_index, device_index,
        )

    @mcp.tool()
    async def poll(
        sub_id: str,
        timeout_seconds: float = 5.0,
        max_events: int = 20,
    ) -> dict[str, Any]:
        """Collect events from a subscription.

        Drains the event queue. If empty, blocks up to timeout_seconds waiting
        for the next change. Returns empty events list (not an error) on timeout.
        Each event: {"value": <new_value>}
        """
        return await listen_tools.poll(registry, sub_id, timeout_seconds, max_events)

    @mcp.tool()
    async def unsubscribe(sub_id: str) -> dict[str, Any]:
        """Stop a listener and clean up its subscription."""
        return await listen_tools.unsubscribe(client, registry, sub_id)

    @mcp.tool()
    async def list_subscriptions() -> dict[str, Any]:
        """List all active subscriptions and their queued event counts."""
        return await listen_tools.list_subscriptions(registry)

    # ------------------------------------------------------------------
    # Rack chain traversal tools (requires AbleOscRack Remote Script)
    # ------------------------------------------------------------------

    if rack_client is not None:

        @mcp.tool()
        async def get_rack_chains(track_index: int, device_index: int) -> dict[str, Any]:
            """List the chains inside a rack device (Instrument Rack, Audio Effect Rack,
            Drum Rack). Requires AbleOscRack Remote Script installed in Ableton Live."""
            return await rack_tools.get_rack_chains(rack_client, track_index, device_index)

        @mcp.tool()
        async def get_chain_devices(
            track_index: int, device_index: int, chain_index: int
        ) -> dict[str, Any]:
            """List the devices inside a rack chain, including their class names and
            whether any are themselves racks (can_have_chains)."""
            return await rack_tools.get_chain_devices(
                rack_client, track_index, device_index, chain_index
            )

        @mcp.tool()
        async def get_chain_device_parameters(
            track_index: int,
            device_index: int,
            chain_index: int,
            nested_device_index: int,
        ) -> dict[str, Any]:
            """Get all parameters for a device inside a rack chain: name, value, min, max."""
            return await rack_tools.get_chain_device_parameters(
                rack_client, track_index, device_index, chain_index, nested_device_index
            )

        @mcp.tool()
        async def set_chain_device_parameter(
            track_index: int,
            device_index: int,
            chain_index: int,
            nested_device_index: int,
            param_index: int,
            value: float,
        ) -> dict[str, Any]:
            """Set a parameter on a device inside a rack chain."""
            return await rack_tools.set_chain_device_parameter(
                rack_client,
                track_index,
                device_index,
                chain_index,
                nested_device_index,
                param_index,
                value,
            )

        # ------------------------------------------------------------------
        # Browser tools (requires AbleOscRack Remote Script)
        # ------------------------------------------------------------------

        @mcp.tool()
        async def list_presets(category_name: str, device_name: str) -> dict[str, Any]:
            """List available presets for a device in the Ableton browser.

            Searches the device's preset folder and returns all loadable preset names.

            category_name: e.g. "instruments", "audio_effects"
            device_name: e.g. "Analog", "Auto Filter", "Wavetable"

            Requires AbleOscRack Remote Script installed in Ableton Live."""
            return await browser_tools.list_presets(rack_client, category_name, device_name)

        @mcp.tool()
        async def list_browser_categories() -> dict[str, Any]:
            """List the available Ableton browser category names.

            Categories include: instruments, audio_effects, midi_effects,
            plugins, sounds, drums, user_library.

            Requires AbleOscRack Remote Script installed in Ableton Live."""
            return await browser_tools.list_browser_categories(rack_client)

        @mcp.tool()
        async def list_browser_devices(category_name: str) -> dict[str, Any]:
            """List the loadable devices in a browser category.

            category_name: e.g. "instruments", "audio_effects", "midi_effects"

            Returns the top-level device names shown in that category.
            Use load_device to add one to a track.

            Requires AbleOscRack Remote Script installed in Ableton Live."""
            return await browser_tools.list_browser_devices(rack_client, category_name)

        @mcp.tool()
        async def load_device(
            track_index: int, category_name: str, device_name: str
        ) -> dict[str, Any]:
            """Search for a device by name and load it onto a track.

            Selects the track as the hotswap target then calls browser.load_item().
            Supports partial name matching — e.g. "Analog" matches "Analog".

            track_index: 0-based track index
            category_name: e.g. "instruments", "audio_effects", "midi_effects"
            device_name: Full or partial device name e.g. "Analog", "Auto Filter"

            Returns {"loaded": True, "name": <matched_name>} on success, or
            {"loaded": False} if the device was not found.

            Requires AbleOscRack Remote Script installed in Ableton Live."""
            return await browser_tools.load_device(
                rack_client, track_index, category_name, device_name
            )

    return mcp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the AbleOscMcp server."""
    host = os.getenv("ABLEOSC_HOST", "127.0.0.1")
    send_port = int(os.getenv("ABLEOSC_SEND_PORT", "11000"))
    receive_port = int(os.getenv("ABLEOSC_RECEIVE_PORT", "11001"))
    rack_send_port = int(os.getenv("ABLEOSC_RACK_SEND_PORT", "11002"))
    rack_receive_port = int(os.getenv("ABLEOSC_RACK_RECEIVE_PORT", "11003"))

    async def run() -> None:
        client = OscClient(host=host, send_port=send_port, receive_port=receive_port)
        await client.start()

        rack_client = OscClient(host=host, send_port=rack_send_port, receive_port=rack_receive_port)
        await rack_client.start()

        try:
            alive = await client.ping()
            if alive:
                logger.info("Connected to AbletonOSC")
            else:
                logger.warning(
                    "AbletonOSC did not respond to ping. "
                    "Is Ableton Live running with the AbletonOSC Remote Script active?"
                )

            rack_alive = await rack_client.ping()
            if rack_alive:
                logger.info("Connected to AbleOscRack — rack chain tools enabled")
            else:
                logger.warning(
                    "AbleOscRack did not respond to ping. "
                    "Rack chain tools will not be available. "
                    "Install the AbleOscRack Remote Script to enable them."
                )
                await rack_client.stop()
                rack_client = None

            mcp = create_server(client, rack_client)
            await mcp.run_stdio_async()
        finally:
            await client.stop()
            if rack_client is not None:
                await rack_client.stop()

    asyncio.run(run())


if __name__ == "__main__":
    main()
