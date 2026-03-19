#!/usr/bin/env python3
"""Generate yao_attributes.json with 384 records (64 hexagrams × 6 yao positions).

This script generates yao (line) attributes for all 64 hexagrams including:
- line_id, hexagram_id, position
- na_jia (stem-branch)
- wuxing (from branch)
- liu_qin (based on wuxing relationship)
- is_shi, is_ying (from shi_ying.json)
- is_fei, is_fu (false for M1)
"""

import json
from pathlib import Path
import sys

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.yao_math import (
    get_na_jia,
    get_wuxing,
    get_wuxing_from_branch,
    get_liu_qin,
    get_palace,
    get_generation,
)


# Load reference data
def load_data():
    """Load all reference data."""
    hexagrams_file = Path(__file__).parent.parent / "data/hexagrams.json"
    shi_ying_file = Path(__file__).parent.parent / "data/shi_ying.json"
    
    with open(hexagrams_file, "r", encoding="utf-8") as f:
        hexagrams = json.load(f)
    
    with open(shi_ying_file, "r", encoding="utf-8") as f:
        shi_ying = json.load(f)
    
    return hexagrams, shi_ying


def get_yao_attributes(hexagram_id: int, position: int, hex_data: dict, shi_data: dict) -> dict:
    """Generate yao attributes for a single position.
    
    Args:
        hexagram_id: Hexagram ID (1-64)
        position: Yao position (1-6, from bottom to top)
        hex_data: Hexagram data from hexagrams.json
        shi_data: Shi-ying data from shi_ying.json
    
    Returns:
        Dictionary with yao attributes
    """
    # Get trigram for this position
    # Position 1-3 use lower_trigram, position 4-6 use upper_trigram
    if position <= 3:
        trigram = hex_data["lower_trigram"]
    else:
        trigram = hex_data["upper_trigram"]
    
    # Determine if this position is yang or yin
    # In binary_code: 1=yang, 0=yin
    is_yang = hex_data["binary_code"][position - 1] == 1
    
    # Get na-jia (stem-branch)
    stem, branch = get_na_jia(trigram, position, is_yang)
    
    # Get wuxing from BRANCH (not stem)
    yao_wuxing = get_wuxing_from_branch(branch)
    
    # Get palace wuxing
    palace_wuxing = shi_data["palace_wuxing"]
    
    # Get liu-qin
    liu_qin = get_liu_qin(yao_wuxing, palace_wuxing)
    
    # Determine is_shi and is_ying
    is_shi = (position == shi_data["shi_position"])
    is_ying = (position == shi_data["ying_position"])
    
    return {
        "line_id": f"{hexagram_id}-{position}",
        "hexagram_id": hexagram_id,
        "position": position,
        "na_jia_gan": stem,
        "na_jia_zhi": branch,
        "wuxing": yao_wuxing,
        "liu_qin": liu_qin,
        "is_shi": is_shi,
        "is_ying": is_ying,
        "is_fei": False,
        "is_fu": False,
    }


def generate_all_yao_attributes():
    """Generate yao attributes for all 64 hexagrams."""
    hexagrams, shi_ying_data = load_data()
    
    # Create shi_ying lookup by hexagram_id
    shi_ying_lookup = {r["hexagram_id"]: r for r in shi_ying_data}
    
    records = []
    
    for hex_id in range(1, 65):
        hex_data = hexagrams[str(hex_id)]
        shi_data = shi_ying_lookup[hex_id]
        
        for pos in range(1, 7):
            yao_attrs = get_yao_attributes(hex_id, pos, hex_data, shi_data)
            records.append(yao_attrs)
    
    return records


def main():
    # Generate records
    records = generate_all_yao_attributes()
    
    # Write to file
    output_file = Path(__file__).parent.parent / "data/yao_attributes.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Generated {len(records)} records to {output_file}")
    
    # Verify key hexagrams
    print(f"  乾卦六爻 (id=1-6):")
    for r in records[:6]:
        print(f"    pos={r['position']}: {r['na_jia_gan']}{r['na_jia_zhi']}, wuxing={r['wuxing']}, liu_qin={r['liu_qin']}, is_shi={r['is_shi']}, is_ying={r['is_ying']}")
    
    print()
    qian_6 = next((r for r in records if r["line_id"] == "1-6"), None)
    print(f"  乾卦 position 6 (is_shi): {qian_6['is_shi']}, liu_qin={qian_6['liu_qin']}")


if __name__ == "__main__":
    main()
