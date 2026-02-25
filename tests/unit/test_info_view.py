"""Unit tests for ableosc.info_view OCR parser."""

import pytest
from ableosc.info_view import _parse_ocr_lines, _is_ui_section_start


class TestIsUiSectionStart:
    def test_operator_header(self):
        assert _is_ui_section_start("Operator W") is True

    def test_operator_with_bullet(self):
        assert _is_ui_section_start("• Operator W") is True

    def test_operator_lowercase(self):
        assert _is_ui_section_start("operator w") is True

    def test_description_line(self):
        assert _is_ui_section_start("This defines the center frequency") is False

    def test_short_word(self):
        assert _is_ui_section_start("Coarse") is False

    def test_empty(self):
        assert _is_ui_section_start("") is False


class TestParseOcrLines:
    def test_title_and_body(self):
        lines = [
            "Filter Frequency",
            "This defines the center or cutoff frequency of the filter.",
            "Note that the resulting frequency may also be modulated",
            "by note velocity and by the filter envelope.",
            "Operator W",
            "Coarse",
            "Fine",
        ]
        title, text = _parse_ocr_lines(lines)
        assert title == "Filter Frequency"
        assert "center or cutoff frequency" in text
        assert "filter envelope" in text
        assert "Coarse" not in text

    def test_title_only_no_body(self):
        # Some controls have no description (e.g. On/Off toggles)
        lines = [
            "Osc D On/Off",
            "• Operator W",
            "Coarse",
            "Fine",
        ]
        title, text = _parse_ocr_lines(lines)
        assert title == "Osc D On/Off"
        assert text == ""

    def test_multi_sentence_body(self):
        lines = [
            "LFO Range",
            "Set the LFO frequency range with this chooser.",
            "• L (Low): 50 seconds to 30 Hz",
            "• H (High): 8 Hz to 12 kHz",
            "Because the LFO is capable of such high frequencies,",
            "it can also function as a fifth oscillator.",
            "• Operator W",
            "Coarse",
        ]
        title, text = _parse_ocr_lines(lines)
        assert title == "LFO Range"
        assert "50 seconds to 30 Hz" in text
        assert "fifth oscillator" in text

    def test_empty_input(self):
        assert _parse_ocr_lines([]) == (None, None)

    def test_single_line_is_title(self):
        title, text = _parse_ocr_lines(["Volume"])
        assert title == "Volume"
        assert text == ""

    def test_real_osc_a_shell(self):
        # Real OCR output from session
        lines = [
            "Osc A Shell",
            "From the shell, you can adjust this",
            "section's most importent paremeters.",
            "clicking on this section of the shell will",
            "open Osc us detailed parameters in the",
            "display.",
            "Operator W",
            "Coarse",
            "Fine",
            "Fixed Level",
        ]
        title, text = _parse_ocr_lines(lines)
        assert title == "Osc A Shell"
        assert "shell" in text.lower()
        assert "Operator" not in text

    def test_real_volume_envelope_attack(self):
        lines = [
            "Volume Envelope Attack Time",
            "The time needed to travel from the Initial",
            "value to the Peak value.",
            "Operator W",
            "Coarse",
        ]
        title, text = _parse_ocr_lines(lines)
        assert title == "Volume Envelope Attack Time"
        assert "Peak value" in text
