"""Unit tests for ableosc.tools.music."""

import pytest
from tests.conftest import MockOscClient
from ableosc.tools import music as music_tools


# ---------------------------------------------------------------------------
# generate_chord  (pure, no client needed)
# ---------------------------------------------------------------------------

class TestGenerateChord:
    async def test_c_major(self):
        result = await music_tools.generate_chord("C", "major", octave=4)
        assert result["pitches"] == [60, 64, 67]
        assert result["root"] == "C"
        assert result["quality"] == "major"

    async def test_dm7(self):
        result = await music_tools.generate_chord("D", "m7", octave=4)
        assert result["pitches"] == [62, 65, 69, 72]

    async def test_note_names_present(self):
        result = await music_tools.generate_chord("C", "major", octave=4)
        assert "C4" in result["note_names"]
        assert "E4" in result["note_names"]
        assert "G4" in result["note_names"]

    async def test_open_voicing(self):
        close = await music_tools.generate_chord("Cmaj7", voicing="close", octave=4)
        open_ = await music_tools.generate_chord("Cmaj7", voicing="open", octave=4)
        assert max(open_["pitches"]) - min(open_["pitches"]) > \
               max(close["pitches"]) - min(close["pitches"])

    async def test_unknown_quality_raises(self):
        with pytest.raises(ValueError):
            await music_tools.generate_chord("C", "xyz", octave=4)


# ---------------------------------------------------------------------------
# add_notes_in_scale
# ---------------------------------------------------------------------------

class TestAddNotesInScale:
    def _note(self, pitch, start=0.0):
        return {"pitch": pitch, "start_time": start, "duration": 0.5, "velocity": 100, "mute": 0}

    async def test_in_scale_notes_unchanged(self):
        client = MockOscClient()
        notes = [self._note(60), self._note(62), self._note(64)]  # C D E — C major
        result = await music_tools.add_notes_in_scale(
            client, 0, 0, notes, "C", "major"
        )
        sent_pitches = [n["pitch"] for n in result["snapped_notes"]]
        assert sent_pitches == [60, 62, 64]

    async def test_out_of_scale_notes_snapped(self):
        client = MockOscClient()
        notes = [self._note(61)]  # C# → should snap to D in C major
        result = await music_tools.add_notes_in_scale(
            client, 0, 0, notes, "C", "major"
        )
        assert result["snapped_notes"][0]["pitch"] == 62

    async def test_returns_scale_info(self):
        client = MockOscClient()
        result = await music_tools.add_notes_in_scale(
            client, 0, 0, [self._note(60)], "A", "minor"
        )
        assert result["scale_root"] == "A"
        assert result["scale_name"] == "minor"


# ---------------------------------------------------------------------------
# transpose_clip
# ---------------------------------------------------------------------------

class TestTransposeClip:
    def _note(self, pitch, start=0.0):
        return {"pitch": pitch, "start_time": start, "duration": 0.5, "velocity": 100, "mute": 0}

    async def test_transpose_up_octave(self):
        client = MockOscClient()
        notes = [self._note(60), self._note(64), self._note(67)]
        # Mock get_notes to return our notes (with track/clip prefix)
        client.when_get("/live/clip/get/notes", 0, 0, 60, 64, 67)
        # Actually need to use the proper response format for get_notes
        # get_notes response: (track_index, clip_index, num_notes, p1, st1, dur1, vel1, mute1, ...)
        client.when_get(
            "/live/clip/get/notes",
            0, 0,          # track, clip prefix
            3,             # note count
            60, 0.0, 0.5, 100, 0,
            64, 0.0, 0.5, 100, 0,
            67, 0.0, 0.5, 100, 0,
        )
        result = await music_tools.transpose_clip(client, 0, 0, 12)
        assert result["transposed"] == 3
        assert result["semitones"] == 12

    async def test_empty_clip_returns_zero(self):
        client = MockOscClient()
        # Empty notes response
        client.when_get("/live/clip/get/notes", 0, 0, 0)
        result = await music_tools.transpose_clip(client, 0, 0, 7)
        assert result["transposed"] == 0


# ---------------------------------------------------------------------------
# quantize_clip
# ---------------------------------------------------------------------------

class TestQuantizeClip:
    async def test_quantize_calls_remove_and_add(self):
        client = MockOscClient()
        # One note slightly off-grid
        client.when_get(
            "/live/clip/get/notes",
            0, 0, 1,
            60, 0.1, 0.5, 100, 0,
        )
        result = await music_tools.quantize_clip(client, 0, 0, grid=0.25)
        assert result["quantized"] == 1
        assert result["grid"] == 0.25
        # Verify remove_notes was called
        assert any("/live/clip/remove/notes" in addr for addr in client.sends)

    async def test_empty_clip(self):
        client = MockOscClient()
        client.when_get("/live/clip/get/notes", 0, 0, 0)
        result = await music_tools.quantize_clip(client, 0, 0)
        assert result["quantized"] == 0

    async def test_invalid_grid_raises(self):
        client = MockOscClient()
        with pytest.raises(ValueError):
            await music_tools.quantize_clip(client, 0, 0, grid=0)

    async def test_invalid_amount_raises(self):
        client = MockOscClient()
        with pytest.raises(ValueError):
            await music_tools.quantize_clip(client, 0, 0, amount=2.0)


# ---------------------------------------------------------------------------
# humanize_clip
# ---------------------------------------------------------------------------

class TestHumanizeClip:
    async def test_humanize_modifies_notes(self):
        client = MockOscClient()
        client.when_get(
            "/live/clip/get/notes",
            0, 0, 2,
            60, 1.0, 0.5, 100, 0,
            64, 2.0, 0.5, 100, 0,
        )
        result = await music_tools.humanize_clip(client, 0, 0)
        assert result["humanized"] == 2
        assert result["timing_amount"] == 0.02
        assert result["velocity_amount"] == 10

    async def test_empty_clip(self):
        client = MockOscClient()
        client.when_get("/live/clip/get/notes", 0, 0, 0)
        result = await music_tools.humanize_clip(client, 0, 0)
        assert result["humanized"] == 0

    async def test_negative_timing_raises(self):
        client = MockOscClient()
        with pytest.raises(ValueError):
            await music_tools.humanize_clip(client, 0, 0, timing_amount=-0.1)
