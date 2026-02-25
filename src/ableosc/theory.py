"""
Music theory primitives: scales, chords, intervals, and MIDI note operations.

All pitch values are MIDI note numbers (0–127, middle C = 60).
"""

from __future__ import annotations

import random
from typing import TypedDict

# ---------------------------------------------------------------------------
# Note name / pitch class mappings
# ---------------------------------------------------------------------------

NOTE_TO_PC: dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

PC_TO_NOTE: dict[int, str] = {
    0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B",
}


def parse_note(name: str) -> int:
    """
    Parse a note name with optional octave to a MIDI pitch.

    Examples:
        "C"   → 60  (middle C, octave 4 default)
        "C4"  → 60
        "A4"  → 69
        "Bb3" → 58
        "F#5" → 78
    """
    name = name.strip()
    # Split letter(s) from trailing octave digit
    i = 0
    while i < len(name) and not name[i].lstrip("-").isdigit():
        i += 1
    note_part = name[:i]
    oct_part = name[i:] if i < len(name) else "4"

    if note_part not in NOTE_TO_PC:
        raise ValueError(f"Unknown note name: {note_part!r}")

    pc = NOTE_TO_PC[note_part]
    octave = int(oct_part)
    midi = (octave + 1) * 12 + pc
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI pitch {midi} out of range (0–127)")
    return midi


# ---------------------------------------------------------------------------
# Scale definitions  (intervals in semitones from root)
# ---------------------------------------------------------------------------

SCALES: dict[str, list[int]] = {
    # Diatonic modes
    "major":           [0, 2, 4, 5, 7, 9, 11],
    "ionian":          [0, 2, 4, 5, 7, 9, 11],
    "dorian":          [0, 2, 3, 5, 7, 9, 10],
    "phrygian":        [0, 1, 3, 5, 7, 8, 10],
    "lydian":          [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":      [0, 2, 4, 5, 7, 9, 10],
    "aeolian":         [0, 2, 3, 5, 7, 8, 10],
    "minor":           [0, 2, 3, 5, 7, 8, 10],
    "locrian":         [0, 1, 3, 5, 6, 8, 10],
    # Minor variants
    "harmonic_minor":  [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor":   [0, 2, 3, 5, 7, 9, 11],
    # Pentatonics
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    # Blues
    "blues":           [0, 3, 5, 6, 7, 10],
    "blues_major":     [0, 2, 3, 4, 7, 9],
    # Symmetric
    "whole_tone":      [0, 2, 4, 6, 8, 10],
    "diminished":      [0, 2, 3, 5, 6, 8, 9, 11],   # whole-half
    "diminished_half": [0, 1, 3, 4, 6, 7, 9, 10],   # half-whole
    "chromatic":       list(range(12)),
    # Other
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],
    "hungarian_minor":   [0, 2, 3, 6, 7, 8, 11],
}

SCALE_ALIASES: dict[str, str] = {
    "nat_minor": "minor",
    "natural_minor": "minor",
    "maj": "major",
    "min": "minor",
    "pent_major": "pentatonic_major",
    "pent_minor": "pentatonic_minor",
}


def resolve_scale(name: str) -> list[int]:
    """Return scale intervals for a name, raising ValueError if unknown."""
    key = name.lower().replace(" ", "_").replace("-", "_")
    key = SCALE_ALIASES.get(key, key)
    if key not in SCALES:
        raise ValueError(
            f"Unknown scale: {name!r}. Known scales: {', '.join(sorted(SCALES))}"
        )
    return SCALES[key]


def scale_pitch_classes(root_pc: int, scale_name: str) -> set[int]:
    """Return the set of pitch classes (0–11) in the given scale."""
    intervals = resolve_scale(scale_name)
    return {(root_pc + i) % 12 for i in intervals}


def snap_to_scale(pitch: int, root_pc: int, scale_name: str) -> int:
    """
    Move a MIDI pitch to the nearest pitch in the given scale.

    If the pitch is already in the scale it is returned unchanged.
    Ties are broken upward.
    """
    intervals = resolve_scale(scale_name)
    pcs = [(root_pc + i) % 12 for i in intervals]

    pc = pitch % 12
    if pc in pcs:
        return pitch

    # Find nearest scale pitch class by chromatic distance
    best_delta = None
    for sp in pcs:
        delta = sp - pc
        # Wrap to [-6, 6]
        if delta > 6:
            delta -= 12
        elif delta <= -6:
            delta += 12
        if best_delta is None or abs(delta) < abs(best_delta):
            best_delta = delta
        elif abs(delta) == abs(best_delta) and delta > best_delta:
            best_delta = delta  # tie-break upward

    return pitch + best_delta


# ---------------------------------------------------------------------------
# Chord definitions  (intervals in semitones from root)
# ---------------------------------------------------------------------------

CHORDS: dict[str, list[int]] = {
    # Triads
    "major":   [0, 4, 7],
    "minor":   [0, 3, 7],
    "dim":     [0, 3, 6],
    "aug":     [0, 4, 8],
    "sus2":    [0, 2, 7],
    "sus4":    [0, 5, 7],
    # Sevenths
    "maj7":    [0, 4, 7, 11],
    "7":       [0, 4, 7, 10],
    "dom7":    [0, 4, 7, 10],
    "m7":      [0, 3, 7, 10],
    "min7":    [0, 3, 7, 10],
    "m7b5":    [0, 3, 6, 10],
    "hdim7":   [0, 3, 6, 10],
    "dim7":    [0, 3, 6, 9],
    "aug7":    [0, 4, 8, 10],
    "augmaj7": [0, 4, 8, 11],
    "mmaj7":   [0, 3, 7, 11],
    # Sixths
    "6":       [0, 4, 7, 9],
    "m6":      [0, 3, 7, 9],
    # Ninths
    "maj9":    [0, 4, 7, 11, 14],
    "9":       [0, 4, 7, 10, 14],
    "m9":      [0, 3, 7, 10, 14],
    "add9":    [0, 4, 7, 14],
    "madd9":   [0, 3, 7, 14],
    # Elevenths
    "11":      [0, 4, 7, 10, 14, 17],
    "maj11":   [0, 4, 7, 11, 14, 17],
    "m11":     [0, 3, 7, 10, 14, 17],
    # Thirteenths
    "13":      [0, 4, 7, 10, 14, 17, 21],
    "maj13":   [0, 4, 7, 11, 14, 17, 21],
}

CHORD_ALIASES: dict[str, str] = {
    "M":    "major",
    "m":    "minor",
    "":     "major",
    "min":  "minor",
    "maj":  "major",
    "dominant7": "7",
    "dom":  "7",
    "half-dim": "m7b5",
    "ø":    "m7b5",
    "o":    "dim",
    "o7":   "dim7",
    "+":    "aug",
    "+7":   "aug7",
}

# Chord symbol parser — splits "Dm7" into root="D", quality="m7"
# or "F#maj7" into root="F#", quality="maj7"
_ROOT_PATTERN_PRIORITY = sorted(NOTE_TO_PC.keys(), key=len, reverse=True)


def parse_chord(symbol: str) -> tuple[int, list[int]]:
    """
    Parse a chord symbol like "Dm7", "F#maj7", "Bb7", "C" into
    (root_midi_pitch_class, intervals).

    Root pitch class is 0–11 (no octave implied here).
    """
    symbol = symbol.strip()
    root_name = None
    for candidate in _ROOT_PATTERN_PRIORITY:
        if symbol.startswith(candidate):
            root_name = candidate
            break
    if root_name is None:
        raise ValueError(f"Cannot parse chord root from: {symbol!r}")

    root_pc = NOTE_TO_PC[root_name]
    quality = symbol[len(root_name):]

    # Normalise quality
    q = CHORD_ALIASES.get(quality, quality)
    if q not in CHORDS:
        raise ValueError(
            f"Unknown chord quality: {quality!r} in {symbol!r}. "
            f"Known qualities: {', '.join(sorted(CHORDS))}"
        )

    return root_pc, CHORDS[q]


def chord_pitches(symbol: str, octave: int = 4, voicing: str = "close") -> list[int]:
    """
    Return MIDI pitches for a chord symbol.

    Args:
        symbol: Chord symbol e.g. "Dm7", "F#maj7", "Bb7"
        octave: Octave for the root (default 4, middle octave)
        voicing: "close" (default) or "open" (spread across two octaves)

    Returns:
        Sorted list of MIDI pitches.
    """
    root_pc, intervals = parse_chord(symbol)
    root_midi = (octave + 1) * 12 + root_pc
    if not 0 <= root_midi <= 127:
        raise ValueError(f"Root MIDI pitch {root_midi} out of range for octave {octave}")

    pitches = [root_midi + i for i in intervals]

    if voicing == "open":
        # Spread: alternate notes up an octave to create an open voicing
        result = [pitches[0]]
        for i, p in enumerate(pitches[1:], 1):
            result.append(p + 12 if i % 2 == 0 else p)
        pitches = result

    pitches = [p for p in pitches if 0 <= p <= 127]
    return sorted(pitches)


# ---------------------------------------------------------------------------
# MIDI note operations
# ---------------------------------------------------------------------------

class NoteDict(TypedDict):
    pitch: int
    start_time: float
    duration: float
    velocity: int
    mute: int


def quantize_notes(
    notes: list[NoteDict],
    grid: float,
    amount: float = 1.0,
) -> list[NoteDict]:
    """
    Snap note start_times to the nearest grid position.

    Args:
        notes: List of note dicts with at least 'start_time'.
        grid: Grid size in beats (e.g. 0.25 = 1/16 note at 1 beat = quarter note).
        amount: 0.0 = no change, 1.0 = full snap (default 1.0).

    Returns:
        New list of notes with adjusted start_times.
    """
    if grid <= 0:
        raise ValueError(f"grid must be positive, got {grid}")
    if not 0.0 <= amount <= 1.0:
        raise ValueError(f"amount must be 0.0–1.0, got {amount}")

    result = []
    for note in notes:
        snapped = round(note["start_time"] / grid) * grid
        new_time = note["start_time"] + (snapped - note["start_time"]) * amount
        result.append({**note, "start_time": max(0.0, new_time)})
    return result


def humanize_notes(
    notes: list[NoteDict],
    timing_amount: float = 0.02,
    velocity_amount: int = 10,
    seed: int | None = None,
) -> list[NoteDict]:
    """
    Add subtle random variations to note start_time and velocity.

    Args:
        notes: List of note dicts.
        timing_amount: Max timing offset in beats (default 0.02 ≈ 5ms at 120BPM).
        velocity_amount: Max velocity offset ±N (default 10).
        seed: Optional random seed for reproducibility.

    Returns:
        New list of notes with humanised values.
    """
    rng = random.Random(seed)
    result = []
    for note in notes:
        t_offset = rng.uniform(-timing_amount, timing_amount)
        v_offset = rng.randint(-velocity_amount, velocity_amount)
        result.append({
            **note,
            "start_time": max(0.0, note["start_time"] + t_offset),
            "velocity": max(1, min(127, note["velocity"] + v_offset)),
        })
    return result


def transpose_notes(notes: list[NoteDict], semitones: int) -> list[NoteDict]:
    """
    Shift all note pitches by the given number of semitones.
    Notes that would go out of MIDI range (0–127) are clamped.
    """
    result = []
    for note in notes:
        new_pitch = note["pitch"] + semitones
        if 0 <= new_pitch <= 127:
            result.append({**note, "pitch": new_pitch})
        # silently drop out-of-range notes
    return result


def snap_notes_to_scale(
    notes: list[NoteDict],
    root: str,
    scale_name: str,
) -> list[NoteDict]:
    """
    Move each note's pitch to the nearest pitch in the given scale.

    Args:
        notes: List of note dicts.
        root: Root note name e.g. "C", "F#", "Bb".
        scale_name: Scale name e.g. "minor", "dorian", "pentatonic_major".

    Returns:
        New list of notes with snapped pitches.
    """
    root_name = root.strip()
    if root_name not in NOTE_TO_PC:
        raise ValueError(f"Unknown root note: {root_name!r}")
    root_pc = NOTE_TO_PC[root_name]

    return [
        {**note, "pitch": snap_to_scale(note["pitch"], root_pc, scale_name)}
        for note in notes
    ]


def notes_to_pitches(notes: list[NoteDict]) -> list[int]:
    """Extract just the pitch values from a list of note dicts."""
    return [n["pitch"] for n in notes]
