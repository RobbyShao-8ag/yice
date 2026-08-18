"""Test data quality for hexagram and lines JSON files."""

import json
import re
import pytest
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


def load_lines():
    """Load lines.json data."""
    with open(DATA_DIR / "lines.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_hexagrams():
    """Load hexagrams.json data."""
    with open(DATA_DIR / "hexagrams.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestLinesDataQuality:
    """Tests for lines.json data quality."""

    def test_lines_count(self):
        """Should have exactly 384 lines (64 hexagrams × 6 lines)."""
        lines = load_lines()
        assert len(lines) == 384, f"Expected 384 lines, got {len(lines)}"

    def test_no_placeholder_text(self):
        """Lines should not contain placeholder text like '初九的爻辞'."""
        lines = load_lines()
        placeholders = ["的爻辞", "待补充", "TBD", "placeholder"]
        for line in lines:
            for placeholder in placeholders:
                assert placeholder not in line.get("text", ""), (
                    f"Placeholder '{placeholder}' found in line {line['id']}"
                )

    def test_text_is_not_empty(self):
        """Canonical lines may be very short (for example, '包羞。')."""
        lines = load_lines()
        for line in lines:
            text = line.get("text", "")
            assert len(text.strip()) >= 2, f"Line {line['id']} is empty"

    def test_required_fields(self):
        """Each line should have required fields."""
        lines = load_lines()
        required = ["id", "hexagram_id", "position", "yao_name", "text"]
        for line in lines:
            for field in required:
                assert field in line, f"Line missing field '{field}': {line.get('id', 'unknown')}"

    def test_position_range(self):
        """Position should be 1-6."""
        lines = load_lines()
        for line in lines:
            pos = line.get("position", 0)
            assert 1 <= pos <= 6, f"Invalid position {pos} in line {line['id']}"

    def test_hexagram_id_range(self):
        """Hexagram ID should be 1-64."""
        lines = load_lines()
        for line in lines:
            hex_id = line.get("hexagram_id", 0)
            assert 1 <= hex_id <= 64, f"Invalid hexagram_id {hex_id} in line {line['id']}"

    def test_source_text_is_chinese_and_traceable(self):
        """Runtime line text should be canonical Chinese with a source URL."""
        for line in load_lines():
            assert re.search(r"[\u4e00-\u9fff]", line.get("source_text", "")), (
                f"Line {line['id']} has no Chinese source text"
            )
            assert line.get("text") == line.get("source_text")
            assert line.get("source", "").startswith(
                "https://zh.wikisource.org/wiki/"
            )
            assert "-{" not in line["source_text"]
            assert "{{" not in line["source_text"]

    def test_yao_names_match_hexagram_binary_code(self):
        """Stored display names must agree with the binary source of truth."""
        from core.yao_lines import get_yao_name

        hexagrams = load_hexagrams()
        for line in load_lines():
            binary_code = hexagrams[str(line["hexagram_id"])]["binary_code"]
            expected = get_yao_name(line["position"], binary_code)
            assert line["yao_name"] == expected, (
                f"Line {line['id']} expected {expected}, got {line['yao_name']}"
            )


class TestHexagramsDataQuality:
    """Tests for hexagrams.json data quality."""

    def test_hexagrams_count(self):
        """Should have 64 hexagrams."""
        hexagrams = load_hexagrams()
        # Handle both dict and list formats
        if isinstance(hexagrams, dict):
            count = len(hexagrams)
        else:
            count = len(hexagrams)
        assert count == 64, f"Expected 64 hexagrams, got {count}"
