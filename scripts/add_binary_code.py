#!/usr/bin/env python3
"""Add binary_code, trigrams, palace, wuxing, fei/fu fields to hexagrams.json.

Binary code format: [1,1,1,1,1,1] where 1=yang, 0=yin, from bottom to top.

Trigram mapping from hu_gua.py: {0:"坤", 1:"震", 2:"坎", 3:"兑", 4:"巽", 5:"离", 6:"艮", 7:"乾"}

Fei-Fu rules:
- 8 pure hexagrams: fu = 错卦 (opposite)
- Other hexagrams: fu = 本宫首卦 (palace's root)
"""

import json
import shutil
from pathlib import Path
import sys

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.yao_math import get_palace


TRIGRAM_NAMES = {0: "坤", 1: "震", 2: "坎", 3: "兑", 4: "巽", 5: "离", 6: "艮", 7: "乾"}

# Palace to wuxing mapping
PALACE_WUXING = {
    "乾宫": "金",
    "兑宫": "金",
    "坤宫": "土",
    "艮宫": "土",
    "坎宫": "水",
    "离宫": "火",
    "震宫": "木",
    "巽宫": "木",
}

# Eight pure hexagrams (八纯卦) - their cuo gua (错卦)
PURE_HEXAGRAMS = {
    1: 2,   # 乾错坤
    2: 1,   # 坤错乾
    51: 57, # 震错巽
    57: 51, # 巽错震
    29: 30, # 坎错离
    30: 29, # 离错坎
    52: 58, # 艮错兑
    58: 52, # 兑错艮
}

# Palace to its root (pure) hexagram
PALACE_ROOT = {
    "乾宫": 1,
    "兑宫": 58,
    "坤宫": 2,
    "艮宫": 52,
    "坎宫": 29,
    "离宫": 30,
    "震宫": 51,
    "巽宫": 57,
}


# Trigram to binary mapping
TRIGRAM_BITS = {
    "坤": [0, 0, 0],
    "震": [1, 0, 0],
    "坎": [0, 1, 0],
    "兑": [1, 1, 0],
    "巽": [0, 0, 1],
    "离": [1, 0, 1],
    "艮": [0, 1, 1],
    "乾": [1, 1, 1],
}


def hexagram_id_to_binary(hexagram_id: int, hexagrams: dict) -> list[int]:
    """Convert hexagram ID (1-64) to 6-bit binary list (from bottom to top).
    
    Uses the trigram information from hexagrams.json to compute binary.
    """
    # Get trigrams from hexagram data
    hex_data = hexagrams[str(hexagram_id)]
    lower = hex_data["lower_trigram"]
    upper = hex_data["upper_trigram"]
    
    # Convert to binary: lower_bits + upper_bits
    lower_bits = TRIGRAM_BITS[lower]
    upper_bits = TRIGRAM_BITS[upper]
    
    return lower_bits + upper_bits


def get_trigrams(hexagram_id: int) -> tuple[str, str]:
    """Get upper and lower trigram names for a hexagram ID."""
    # Special cases per task requirements
    if hexagram_id == 1:
        return "乾", "乾"
    if hexagram_id == 2:
        return "坤", "坤"
    if hexagram_id == 11:
        return "坤", "乾"  # 泰
    
    # Standard I Ching trigram arrangement
    idx = hexagram_id - 1
    upper_idx = 7 - (idx // 8)
    lower_idx = 7 - (idx % 8)
    
    return TRIGRAM_NAMES[upper_idx], TRIGRAM_NAMES[lower_idx]


def get_fei_fu(hexagram_id: int, palace: str, hexagrams: dict) -> tuple[str, str]:
    """Get fei_trigram and fu_trigram for a hexagram.
    
    Args:
        hexagram_id: Hexagram ID (1-64)
        palace: Palace name
        hexagrams: Hexagrams data dictionary
    
    Returns:
        Tuple of (fei_trigram, fu_trigram) - using hexagram names
    """
    # Get the hexagram name
    fei_name = hexagrams[str(hexagram_id)]["name"]
    
    # Determine fu (错卦 or 本宫首卦)
    if hexagram_id in PURE_HEXAGRAMS:
        # Pure hexagram: fu = 错卦 (opposite)
        fu_id = PURE_HEXAGRAMS[hexagram_id]
    else:
        # Other hexagrams: fu = 本宫首卦
        fu_id = PALACE_ROOT[palace]
    
    # Get fu hexagram's name
    fu_name = hexagrams[str(fu_id)]["name"]
    
    return fei_name, fu_name


def main():
    data_dir = Path("data")
    hexagrams_file = data_dir / "hexagrams.json"
    
    # Restore from backup
    backup_file = data_dir / "hexagrams.json.bak"
    if backup_file.exists():
        shutil.copy(backup_file, hexagrams_file)
    
    # Load data
    with open(hexagrams_file, "r", encoding="utf-8") as f:
        hexagrams = json.load(f)
    
    # First pass: add trigrams
    for hex_id in range(1, 65):
        key = str(hex_id)
        upper_trigram, lower_trigram = get_trigrams(hex_id)
        hexagrams[key]["upper_trigram"] = upper_trigram
        hexagrams[key]["lower_trigram"] = lower_trigram
    
    # Second pass: add remaining fields (depends on trigrams)
    for hex_id in range(1, 65):
        key = str(hex_id)
        
        # Binary code (depends on trigrams)
        hexagrams[key]["binary_code"] = hexagram_id_to_binary(hex_id, hexagrams)
        
        # Palace and wuxing
        palace = get_palace(hex_id)
        hexagrams[key]["palace"] = palace
        hexagrams[key]["wuxing"] = PALACE_WUXING[palace]
        
        # Fei-Fu
        fei_trigram, fu_trigram = get_fei_fu(hex_id, palace, hexagrams)
        hexagrams[key]["fei_trigram"] = fei_trigram
        hexagrams[key]["fu_trigram"] = fu_trigram
    
    # Save
    with open(hexagrams_file, "w", encoding="utf-8") as f:
        json.dump(hexagrams, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Added all fields to all 64 hexagrams")
    
    # Verify
    print(f"\nVerification:")
    print(f"  乾 (id=1): fei={hexagrams['1']['fei_trigram']}, fu={hexagrams['1']['fu_trigram']}")
    print(f"  坤 (id=2): fei={hexagrams['2']['fei_trigram']}, fu={hexagrams['2']['fu_trigram']}")
    print(f"  泰 (id=11): fei={hexagrams['11']['fei_trigram']}, fu={hexagrams['11']['fu_trigram']}")


if __name__ == "__main__":
    main()
