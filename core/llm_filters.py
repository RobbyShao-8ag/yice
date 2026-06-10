"""Utilities for normalizing LLM text output."""

import re


_THINK_BLOCK_PATTERNS = [
    r"hlen\s*\n.*?\n\s*hline\s*(?:\n|$)",
    r"hlen\s*.*?\s*hline",
    r"hlen\s*.*?\s*hlen",
    r"<think\b[^>]*>.*?</think>",
    r"\|think\|.*?\|think\|",
    r"\(think\).*?\(think\)",
    r"\[think\].*?(?:\[/think\]|\[think\])",
]


def filter_think_content(text: str) -> str:
    """Remove provider reasoning blocks from model-visible content."""
    if not text:
        return ""

    filtered = text
    for pattern in _THINK_BLOCK_PATTERNS:
        filtered = re.sub(pattern, "", filtered, flags=re.DOTALL | re.IGNORECASE)

    return _strip_standalone_markers(filtered).strip()


def _strip_standalone_markers(text: str) -> str:
    markers = {"hlen", "hline", "think", "|think|", "(think)", "[think]", "[/think]"}
    return "\n".join(
        line for line in text.splitlines() if line.strip().lower() not in markers
    )
