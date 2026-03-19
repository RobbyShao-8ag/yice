#!/usr/bin/env python3
"""Generate shi_ying.json with 64 records of palace, generation, and shi/ying positions.

This script uses:
- get_palace() and get_generation() from core/yao_math.py
- shiying_reference.json for shi position lookup
- Formula: ying_position = (shi + 2) % 6 + 1
"""

import json
from pathlib import Path
import sys

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.yao_math import get_palace, get_generation


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


def load_shiying_reference() -> dict:
    """Load shiying reference data."""
    ref_file = Path(__file__).parent.parent / "tests/fixtures/reference/shiying_reference.json"
    with open(ref_file, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_ying_position(shi_position: int) -> int:
    """Calculate ying position from shi position.
    
    Formula: ying = (shi + 2) % 6 + 1
    """
    return (shi_position + 2) % 6 + 1


def generate_shi_ying() -> list[dict]:
    """Generate shi_ying data for all 64 hexagrams."""
    shiying_ref = load_shiying_reference()
    generation_positions = shiying_ref["generation_positions"]
    
    records = []
    
    for hex_id in range(1, 65):
        palace = get_palace(hex_id)
        generation = get_generation(hex_id)
        
        # Get shi position from reference
        gen_info = generation_positions[generation]
        shi_position = gen_info["shi_position"]
        ying_position = gen_info["ying_position"]
        
        record = {
            "hexagram_id": hex_id,
            "palace": palace,
            "palace_wuxing": PALACE_WUXING[palace],
            "generation": generation,
            "shi_position": shi_position,
            "ying_position": ying_position,
        }
        records.append(record)
    
    return records


def main():
    data_dir = Path(__file__).parent.parent / "data"
    output_file = data_dir / "shi_ying.json"
    
    # Generate data
    records = generate_shi_ying()
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Generated {len(records)} records to {output_file}")
    
    # Verify key hexagrams
    qian = next((r for r in records if r["hexagram_id"] == 1), None)
    print(f"  乾 (id=1): shi={qian['shi_position']}, ying={qian['ying_position']}")
    
    kun = next((r for r in records if r["hexagram_id"] == 2), None)
    print(f"  坤 (id=2): shi={kun['shi_position']}, ying={kun['ying_position']}")
    
    # Validate all 64
    assert len(records) == 64
    assert all(r["shi_position"] and r["ying_position"] for r in records)
    print("✓ All 64 records validated")


if __name__ == "__main__":
    main()
