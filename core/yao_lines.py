"""Canonical helpers for six-line names and yin/yang values.

The hexagram ``binary_code`` is the source of truth.  Display names and
mutual-hexagram calculations must not infer yin/yang from duplicated text
fields in ``lines.json``.
"""

from typing import Any, Sequence


def get_yao_name(position: int, binary_code: Sequence[int]) -> str:
    """Return the canonical Chinese line name for a 1-based position."""
    if not 1 <= position <= 6:
        raise ValueError(f"position must be 1-6, got {position}")
    if len(binary_code) != 6 or any(value not in (0, 1) for value in binary_code):
        raise ValueError("binary_code must contain exactly six 0/1 values")

    numeral = "九" if binary_code[position - 1] == 1 else "六"
    if position == 1:
        return f"初{numeral}"
    if position == 6:
        return f"上{numeral}"
    return f"{numeral}{'二三四五'[position - 2]}"


def get_yao_values(hexagram_data: dict[str, Any]) -> list[int]:
    """Return six canonical yin/yang values from a hexagram data object.

    ``binary_code`` is preferred.  The name-based fallback keeps compatibility
    with small test fixtures and external callers that only provide line names.
    """
    binary_code = hexagram_data.get("binary_code")
    if (
        isinstance(binary_code, list)
        and len(binary_code) == 6
        and all(value in (0, 1) for value in binary_code)
    ):
        return list(binary_code)

    lines = hexagram_data.get("lines", [])
    values: list[int] = []
    for line in lines:
        if not isinstance(line, dict):
            name = str(line)
        else:
            name = str(line.get("yao_name") or line.get("line_name") or "")
        values.append(1 if "九" in name else 0)
    return values
