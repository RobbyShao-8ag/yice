#!/usr/bin/env python3
"""
Fix hexagrams.json using correct reference data from tests/fixtures/reference/hexagram_binary_reference.json

Updates ONLY:
- binary_code
- upper_trigram
- lower_trigram

Preserves ALL other fields unchanged.
"""

import json


def main():
    # Load reference (correct values)
    with open("tests/fixtures/reference/hexagram_binary_reference.json", "r", encoding="utf-8") as f:
        reference = json.load(f)

    # Load current data
    with open("data/hexagrams.json", "r", encoding="utf-8") as f:
        hexagrams = json.load(f)

    # Update only binary_code, upper_trigram, lower_trigram
    updated = 0
    for hex_id, ref_data in reference.items():
        if hex_id in hexagrams:
            hexagrams[hex_id]["binary_code"] = ref_data["binary_code"]
            hexagrams[hex_id]["upper_trigram"] = ref_data["upper_trigram"]
            hexagrams[hex_id]["lower_trigram"] = ref_data["lower_trigram"]
            updated += 1
        else:
            print(f"Warning: Hexagram {hex_id} not found in hexagrams.json")

    print(f"Updated {updated} hexagrams")

    # Write back with 2-space indent
    with open("data/hexagrams.json", "w", encoding="utf-8") as f:
        json.dump(hexagrams, f, indent=2, ensure_ascii=False)

    print("Done! data/hexagrams.json has been fixed.")


if __name__ == "__main__":
    main()
