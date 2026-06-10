"""六卦关系模块 (Hexagram Relations Module).

Functions for calculating hexagram relations:
- 错卦 (Cuo Gua): yin-yang inversion
- 综卦 (Zong Gua): upside-down flip
- 交卦 (Jiao Gua): trigram swap
- 互卦 (Hu Gua): inner trigram swap (from hu_gua.py)
"""

import json
from pathlib import Path
from typing import Optional

# Cache for hexagrams data
_hexagrams_data = None
_BINARY_TO_ID = None
_ID_TO_BINARY = None


def _load_hexagrams() -> dict:
    """Load hexagrams data from JSON."""
    global _hexagrams_data, _BINARY_TO_ID, _ID_TO_BINARY

    if _hexagrams_data is not None:
        return _hexagrams_data

    data_file = Path(__file__).parent.parent / "data/hexagrams.json"
    with open(data_file, "r", encoding="utf-8") as f:
        _hexagrams_data = json.load(f)

    # Build lookup tables
    _BINARY_TO_ID = {}
    _ID_TO_BINARY = {}

    for hex_id in range(1, 65):
        binary = tuple(_hexagrams_data[str(hex_id)]["binary_code"])
        _BINARY_TO_ID[binary] = hex_id
        _ID_TO_BINARY[hex_id] = list(binary)

    return _hexagrams_data


def _binary_to_id(binary: list[int]) -> int:
    """Convert 6-bit binary to hexagram ID.
    
    Args:
        binary: 6-bit list [1/0 from bottom to top]
    
    Returns:
        Hexagram ID (1-64)
    """
    global _BINARY_TO_ID, _ID_TO_BINARY
    
    _load_hexagrams()
    
    key = tuple(binary)
    
    if key in _BINARY_TO_ID:
        return _BINARY_TO_ID[key]
    
    # Binary not in lookup - calculate value and search
    val = 0
    for j, bit in enumerate(binary):
        val |= (bit << j)
    
    # Search all IDs with matching value
    candidates = []
    for hid, bin2 in _ID_TO_BINARY.items():
        v2 = 0
        for j, b in enumerate(bin2):
            v2 |= (b << j)
        if v2 == val:
            candidates.append(hid)
    
    if candidates:
        # Return first candidate that differs from id=2 to avoid ambiguity
        for c in candidates:
            if c != 2:
                return c
        return candidates[0]
    
    raise ValueError(f"Cannot convert binary {binary} to hexagram ID")


def get_cuo_gua(hexagram_id: int) -> int:
    """Get 错卦 (Cuo Gua) - yin-yang inversion.
    
    Inverts all bits: yang→yin, yin→yang
    
    Args:
        hexagram_id: Hexagram ID (1-64)
    
    Returns:
        Cuo Gua hexagram ID
    
    Raises:
        ValueError: If hexagram_id out of range.
    """
    if not 1 <= hexagram_id <= 64:
        raise ValueError(f"Hexagram ID must be 1-64, got {hexagram_id}")
    
    hexagrams = _load_hexagrams()
    binary = hexagrams[str(hexagram_id)]["binary_code"]
    
    # Invert all bits
    inverted = [1 - b for b in binary]
    
    return _binary_to_id(inverted)


def get_zong_gua(hexagram_id: int) -> Optional[int]:
    """Get 综卦 (Zong Gua) - upside-down flip.
    
    Reverses the binary: [1,2,3,4,5,6] → [6,5,4,3,2,1]
    Returns None for 8 self-zong hexagrams.
    
    Args:
        hexagram_id: Hexagram ID (1-64)
    
    Returns:
        Zong Gua hexagram ID, or None if self-zong
    
    Raises:
        ValueError: If hexagram_id out of range.
    """
    if not 1 <= hexagram_id <= 64:
        raise ValueError(f"Hexagram ID must be 1-64, got {hexagram_id}")
    
    hexagrams = _load_hexagrams()
    binary = hexagrams[str(hexagram_id)]["binary_code"]
    
    # Reverse the order
    reversed_binary = binary[::-1]
    
    # Check if self-zong (same as original)
    if binary == reversed_binary:
        return None
    
    return _binary_to_id(reversed_binary)


def get_jiao_gua(hexagram_id: int) -> int:
    """Get 交卦 (Jiao Gua) - trigram swap.
    
    Swaps upper and lower trigrams:
    [a,b,c,d,e,f] → [d,e,f,a,b,c]
    
    Args:
        hexagram_id: Hexagram ID (1-64)
    
    Returns:
        Jiao Gua hexagram ID
    
    Raises:
        ValueError: If hexagram_id out of range.
    """
    if not 1 <= hexagram_id <= 64:
        raise ValueError(f"Hexagram ID must be 1-64, got {hexagram_id}")
    
    hexagrams = _load_hexagrams()
    binary = hexagrams[str(hexagram_id)]["binary_code"]
    
    # Swap: upper[3:6] with lower[0:3]
    swapped = binary[3:6] + binary[0:3]
    
    return _binary_to_id(swapped)


def get_hu_gua(hexagram_id: int) -> int:
    """Get 互卦 (Hu Gua) - inner trigram swap.
    
    Uses trigram positions 2,3,4 for both:
    - Lower trigram: yao 2,3,4
    - Upper trigram: yao 3,4,5
    
    This function imports from hu_gua.py.
    
    Args:
        hexagram_id: Hexagram ID (1-64)
    
    Returns:
        Hu Gua hexagram ID
    
    Raises:
        ValueError: If hexagram_id out of range.
    """
    if not 1 <= hexagram_id <= 64:
        raise ValueError(f"Hexagram ID must be 1-64, got {hexagram_id}")
    
    # Import from hu_gua.py
    from core.hu_gua import calculate_hu_gua
    
    hexagrams = _load_hexagrams()
    binary = hexagrams[str(hexagram_id)]["binary_code"]
    
    # calculate_hu_gua expects list [pos1, pos2, pos3, pos4, pos5, pos6]
    return calculate_hu_gua(hexagram_id, binary)
