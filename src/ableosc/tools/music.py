"""
Musical intelligence tools: chord generation, scale snapping, transpose,
quantize, and humanize.

These tools wrap the theory module and the existing clip/note OSC tools
to give Claude reliable, musically-correct MIDI operations.
"""

from __future__ import annotations

from ableosc import theory
from ableosc.client import OscClient
from ableosc.tools import clip as clip_tools


async def generate_chord(
    root: str,
    quality: str = "major",
    octave: int = 4,
    voicing: str = "close",
) -> dict:
    """
    Generate MIDI pitches for a chord.

    Args:
        root: Root note name e.g. "C", "F#", "Bb"
        quality: Chord quality e.g. "major", "minor", "m7", "maj7", "dim7"
        octave: Octave for the root (4 = middle octave, C4 = MIDI 60)
        voicing: "close" (default) or "open" (spread across two octaves)

    Returns:
        dict with pitches list, root, quality, octave, and name.
    """
    symbol = root + quality if quality not in ("major", "") else root
    pitches = theory.chord_pitches(symbol, octave=octave, voicing=voicing)
    note_names = [
        f"{theory.PC_TO_NOTE[p % 12]}{(p // 12) - 1}" for p in pitches
    ]
    return {
        "pitches": pitches,
        "note_names": note_names,
        "root": root,
        "quality": quality,
        "octave": octave,
        "voicing": voicing,
    }


async def add_notes_in_scale(
    client: OscClient,
    track_index: int,
    clip_index: int,
    notes: list[dict],
    scale_root: str,
    scale_name: str,
) -> dict:
    """
    Add MIDI notes to a clip, snapping each pitch to the nearest scale tone first.

    Args:
        track_index: Track index
        clip_index: Clip slot index
        notes: List of note dicts {pitch, start_time, duration, velocity, mute}
        scale_root: Root note name e.g. "C", "F#", "Bb"
        scale_name: Scale name e.g. "minor", "dorian", "pentatonic_major"

    Returns:
        dict with snapped_notes list and scale info.
    """
    snapped = theory.snap_notes_to_scale(notes, scale_root, scale_name)
    await clip_tools.add_notes(client, track_index, clip_index, snapped)
    return {
        "added": len(snapped),
        "scale_root": scale_root,
        "scale_name": scale_name,
        "snapped_notes": snapped,
    }


async def transpose_clip(
    client: OscClient,
    track_index: int,
    clip_index: int,
    semitones: int,
) -> dict:
    """
    Transpose all notes in a clip by a number of semitones.

    Args:
        track_index: Track index
        clip_index: Clip slot index
        semitones: Number of semitones to shift (positive = up, negative = down)

    Returns:
        dict with note count and semitones shifted.
    """
    result = await clip_tools.get_notes(client, track_index, clip_index)
    notes = result["notes"]
    if not notes:
        return {"transposed": 0, "semitones": semitones}

    transposed = theory.transpose_notes(notes, semitones)
    await clip_tools.remove_notes(client, track_index, clip_index)
    await clip_tools.add_notes(client, track_index, clip_index, transposed)
    return {"transposed": len(transposed), "semitones": semitones}


async def quantize_clip(
    client: OscClient,
    track_index: int,
    clip_index: int,
    grid: float = 0.25,
    amount: float = 1.0,
) -> dict:
    """
    Snap note start times in a clip to a rhythmic grid.

    Args:
        track_index: Track index
        clip_index: Clip slot index
        grid: Grid size in beats. 0.25 = 1/16 note, 0.5 = 1/8 note, 1.0 = 1/4 note
        amount: Quantize strength 0.0–1.0 (default 1.0 = full snap)

    Returns:
        dict with note count and grid info.
    """
    if grid <= 0:
        raise ValueError(f"grid must be positive, got {grid}")
    if not 0.0 <= amount <= 1.0:
        raise ValueError(f"amount must be 0.0–1.0, got {amount}")

    result = await clip_tools.get_notes(client, track_index, clip_index)
    notes = result["notes"]
    if not notes:
        return {"quantized": 0, "grid": grid, "amount": amount}

    quantized = theory.quantize_notes(notes, grid=grid, amount=amount)
    await clip_tools.remove_notes(client, track_index, clip_index)
    await clip_tools.add_notes(client, track_index, clip_index, quantized)
    return {"quantized": len(quantized), "grid": grid, "amount": amount}


async def humanize_clip(
    client: OscClient,
    track_index: int,
    clip_index: int,
    timing_amount: float = 0.02,
    velocity_amount: int = 10,
) -> dict:
    """
    Add subtle random timing and velocity variation to notes in a clip.

    Args:
        track_index: Track index
        clip_index: Clip slot index
        timing_amount: Max timing offset in beats (default 0.02 ≈ 5ms at 120BPM)
        velocity_amount: Max velocity offset ± (default 10)

    Returns:
        dict with note count and humanize parameters.
    """
    if timing_amount < 0:
        raise ValueError(f"timing_amount must be >= 0, got {timing_amount}")
    if velocity_amount < 0:
        raise ValueError(f"velocity_amount must be >= 0, got {velocity_amount}")

    result = await clip_tools.get_notes(client, track_index, clip_index)
    notes = result["notes"]
    if not notes:
        return {"humanized": 0, "timing_amount": timing_amount, "velocity_amount": velocity_amount}

    humanized = theory.humanize_notes(
        notes, timing_amount=timing_amount, velocity_amount=velocity_amount
    )
    await clip_tools.remove_notes(client, track_index, clip_index)
    await clip_tools.add_notes(client, track_index, clip_index, humanized)
    return {
        "humanized": len(humanized),
        "timing_amount": timing_amount,
        "velocity_amount": velocity_amount,
    }
