"""Unit tests for ableosc.theory — scales, chords, note operations."""

import pytest
from ableosc import theory


# ---------------------------------------------------------------------------
# parse_note
# ---------------------------------------------------------------------------

class TestParseNote:
    def test_middle_c(self):
        assert theory.parse_note("C4") == 60

    def test_a440(self):
        assert theory.parse_note("A4") == 69

    def test_default_octave_4(self):
        assert theory.parse_note("C") == 60

    def test_flat(self):
        assert theory.parse_note("Bb3") == 58

    def test_sharp(self):
        assert theory.parse_note("F#5") == 78

    def test_enharmonic(self):
        assert theory.parse_note("C#4") == theory.parse_note("Db4")

    def test_low_note(self):
        assert theory.parse_note("C0") == 12

    def test_high_note(self):
        assert theory.parse_note("G9") == 127

    def test_unknown_note_raises(self):
        with pytest.raises(ValueError, match="Unknown note name"):
            theory.parse_note("X4")


# ---------------------------------------------------------------------------
# resolve_scale
# ---------------------------------------------------------------------------

class TestResolveScale:
    def test_major_intervals(self):
        assert theory.resolve_scale("major") == [0, 2, 4, 5, 7, 9, 11]

    def test_minor_intervals(self):
        assert theory.resolve_scale("minor") == [0, 2, 3, 5, 7, 8, 10]

    def test_alias_maj(self):
        assert theory.resolve_scale("maj") == theory.resolve_scale("major")

    def test_alias_min(self):
        assert theory.resolve_scale("min") == theory.resolve_scale("minor")

    def test_case_insensitive(self):
        assert theory.resolve_scale("Dorian") == theory.resolve_scale("dorian")

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown scale"):
            theory.resolve_scale("mystery_scale")

    def test_pentatonic_minor(self):
        assert theory.resolve_scale("pentatonic_minor") == [0, 3, 5, 7, 10]

    def test_blues(self):
        assert theory.resolve_scale("blues") == [0, 3, 5, 6, 7, 10]


# ---------------------------------------------------------------------------
# snap_to_scale
# ---------------------------------------------------------------------------

class TestSnapToScale:
    def test_in_scale_unchanged(self):
        # C major: C(0) D(2) E(4) F(5) G(7) A(9) B(11)
        assert theory.snap_to_scale(60, 0, "major") == 60  # C4 in C major

    def test_snap_up(self):
        # C# (61) is between C and D in C major — should snap to D (62)
        assert theory.snap_to_scale(61, 0, "major") == 62

    def test_snap_down(self):
        # Eb (63) between D and E — closer to E (64)? No, Eb is 1 away from D, 1 away from E
        # tie breaks upward → E
        result = theory.snap_to_scale(63, 0, "major")
        assert result in (62, 64)  # D or E, implementation may vary on exact tie

    def test_bb_in_c_major_snaps_to_b(self):
        # Bb (70) in C major: nearest are A(69) and B(71) — B is closer
        assert theory.snap_to_scale(70, 0, "major") == 71

    def test_different_root(self):
        # F# (6) in D major (D=2, scale: D E F# G A B C#)
        # F# is in D major, so should be unchanged
        assert theory.snap_to_scale(66, 2, "major") == 66  # F#4 in D major

    def test_different_octave(self):
        # C#5 (73) in C major — should snap to D5 (74)
        assert theory.snap_to_scale(73, 0, "major") == 74


# ---------------------------------------------------------------------------
# chord_pitches
# ---------------------------------------------------------------------------

class TestChordPitches:
    def test_c_major(self):
        assert theory.chord_pitches("C", octave=4) == [60, 64, 67]

    def test_a_minor(self):
        assert theory.chord_pitches("Am", octave=4) == [69, 72, 76]

    def test_d_minor_7(self):
        pitches = theory.chord_pitches("Dm7", octave=4)
        assert pitches == [62, 65, 69, 72]

    def test_fsharp_major_7(self):
        pitches = theory.chord_pitches("F#maj7", octave=4)
        assert 66 in pitches  # F#4

    def test_bb_dominant_7(self):
        pitches = theory.chord_pitches("Bb7", octave=3)
        assert 58 in pitches  # Bb3

    def test_open_voicing_wider_than_close(self):
        close = theory.chord_pitches("Cmaj7", octave=4, voicing="close")
        open_ = theory.chord_pitches("Cmaj7", octave=4, voicing="open")
        assert max(open_) - min(open_) > max(close) - min(close)

    def test_unknown_quality_raises(self):
        with pytest.raises(ValueError):
            theory.chord_pitches("Cxyz", octave=4)

    def test_sorted_output(self):
        pitches = theory.chord_pitches("Dm7", octave=4)
        assert pitches == sorted(pitches)


# ---------------------------------------------------------------------------
# quantize_notes
# ---------------------------------------------------------------------------

class TestQuantizeNotes:
    def _note(self, start_time):
        return {"pitch": 60, "start_time": start_time, "duration": 0.5, "velocity": 100, "mute": 0}

    def test_already_on_grid(self):
        notes = [self._note(0.0), self._note(0.5), self._note(1.0)]
        result = theory.quantize_notes(notes, grid=0.5)
        assert [n["start_time"] for n in result] == [0.0, 0.5, 1.0]

    def test_snaps_off_grid(self):
        notes = [self._note(0.1), self._note(0.9)]
        result = theory.quantize_notes(notes, grid=0.5)
        assert result[0]["start_time"] == pytest.approx(0.0)
        assert result[1]["start_time"] == pytest.approx(1.0)

    def test_partial_amount(self):
        notes = [self._note(0.2)]
        result = theory.quantize_notes(notes, grid=0.5, amount=0.5)
        # 0.2 → halfway between 0.2 and 0.0 = 0.1
        assert result[0]["start_time"] == pytest.approx(0.1)

    def test_negative_start_clamped_to_zero(self):
        notes = [self._note(0.05)]
        result = theory.quantize_notes(notes, grid=0.5, amount=1.0)
        assert result[0]["start_time"] >= 0.0

    def test_invalid_grid_raises(self):
        with pytest.raises(ValueError):
            theory.quantize_notes([], grid=0)

    def test_invalid_amount_raises(self):
        with pytest.raises(ValueError):
            theory.quantize_notes([], grid=0.25, amount=1.5)


# ---------------------------------------------------------------------------
# humanize_notes
# ---------------------------------------------------------------------------

class TestHumanizeNotes:
    def _note(self, pitch=60, start=1.0, vel=100):
        return {"pitch": pitch, "start_time": start, "duration": 0.5, "velocity": vel, "mute": 0}

    def test_produces_same_count(self):
        notes = [self._note() for _ in range(8)]
        result = theory.humanize_notes(notes, seed=42)
        assert len(result) == 8

    def test_timing_variation_within_bounds(self):
        notes = [self._note(start=1.0) for _ in range(50)]
        result = theory.humanize_notes(notes, timing_amount=0.1, seed=0)
        for n in result:
            assert 0.9 <= n["start_time"] <= 1.1

    def test_velocity_clamped(self):
        notes = [self._note(vel=1), self._note(vel=127)]
        result = theory.humanize_notes(notes, velocity_amount=20, seed=0)
        for n in result:
            assert 1 <= n["velocity"] <= 127

    def test_reproducible_with_seed(self):
        notes = [self._note() for _ in range(4)]
        r1 = theory.humanize_notes(notes, seed=99)
        r2 = theory.humanize_notes(notes, seed=99)
        assert r1 == r2

    def test_different_seeds_differ(self):
        notes = [self._note() for _ in range(10)]
        r1 = theory.humanize_notes(notes, seed=1)
        r2 = theory.humanize_notes(notes, seed=2)
        assert r1 != r2


# ---------------------------------------------------------------------------
# transpose_notes
# ---------------------------------------------------------------------------

class TestTransposeNotes:
    def _note(self, pitch):
        return {"pitch": pitch, "start_time": 0.0, "duration": 0.5, "velocity": 100, "mute": 0}

    def test_transpose_up(self):
        notes = [self._note(60), self._note(64), self._note(67)]
        result = theory.transpose_notes(notes, 12)
        assert [n["pitch"] for n in result] == [72, 76, 79]

    def test_transpose_down(self):
        notes = [self._note(60)]
        result = theory.transpose_notes(notes, -12)
        assert result[0]["pitch"] == 48

    def test_out_of_range_dropped(self):
        notes = [self._note(120)]
        result = theory.transpose_notes(notes, 10)  # would be 130, out of range
        assert result == []

    def test_zero_semitones_unchanged(self):
        notes = [self._note(60), self._note(64)]
        result = theory.transpose_notes(notes, 0)
        assert [n["pitch"] for n in result] == [60, 64]


# ---------------------------------------------------------------------------
# snap_notes_to_scale
# ---------------------------------------------------------------------------

class TestSnapNotesToScale:
    def _note(self, pitch):
        return {"pitch": pitch, "start_time": 0.0, "duration": 0.5, "velocity": 100, "mute": 0}

    def test_in_scale_unchanged(self):
        # C major notes
        notes = [self._note(60), self._note(62), self._note(64)]
        result = theory.snap_notes_to_scale(notes, "C", "major")
        assert [n["pitch"] for n in result] == [60, 62, 64]

    def test_out_of_scale_snapped(self):
        # C# (61) in C major → D (62)
        notes = [self._note(61)]
        result = theory.snap_notes_to_scale(notes, "C", "major")
        assert result[0]["pitch"] == 62

    def test_unknown_root_raises(self):
        with pytest.raises(ValueError, match="Unknown root note"):
            theory.snap_notes_to_scale([self._note(60)], "X", "major")

    def test_unknown_scale_raises(self):
        with pytest.raises(ValueError, match="Unknown scale"):
            theory.snap_notes_to_scale([self._note(60)], "C", "not_a_scale")
