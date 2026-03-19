"""Tests for hexagrams.json data integrity.

This test file verifies the correctness of hexagrams.json data after the fix.
All tests should pass now that data/hexagrams.json has been corrected.

Verified:
1. Binary code uniqueness - all 64 hexagrams have unique binary codes
2. Trigram consistency - upper/lower trigrams match binary composition
3. Reference alignment - data matches hexagram_binary_reference.json
"""

import json
import pytest
from pathlib import Path

# Trigram to binary mapping (lower bits first, then upper bits)
TRIGRAM_BINARY = {
    "乾": [1, 1, 1],
    "坤": [0, 0, 0],
    "震": [1, 0, 0],
    "坎": [0, 1, 0],
    "艮": [0, 0, 1],
    "巽": [1, 1, 0],
    "离": [1, 0, 1],
    "兑": [0, 1, 1],
}


def load_hexagrams():
    """Load hexagrams.json data."""
    data_dir = Path(__file__).parent.parent / "data"
    with open(data_dir / "hexagrams.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_reference():
    """Load the reference binary data."""
    ref_path = Path(__file__).parent / "fixtures" / "reference" / "hexagram_binary_reference.json"
    with open(ref_path, "r", encoding="utf-8") as f:
        return json.load(f)


def binary_to_tuple(binary_code):
    """Convert binary list to tuple for comparison."""
    return tuple(binary_code)


def trigram_from_binary(binary_code):
    """Extract trigrams from binary code.
    
    Binary format: [lower_bit1, lower_bit2, lower_bit3, upper_bit1, upper_bit2, upper_bit3]
    Returns: (upper_trigram_name, lower_trigram_name)
    """
    lower_bits = binary_code[:3]
    upper_bits = binary_code[3:6]
    
    # Find matching trigrams
    for trigram, bits in TRIGRAM_BINARY.items():
        if tuple(bits) == tuple(lower_bits):
            lower = trigram
        if tuple(bits) == tuple(upper_bits):
            upper = trigram
    
    return upper, lower


class TestBinaryCodeUniqueness:
    """Test that all hexagrams have unique binary codes."""

    def test_all_binary_codes_unique(self):
        """All 64 hexagrams should have unique binary_code values."""
        hexagrams = load_hexagrams()
        
        binary_codes = []
        for hex_id in hexagrams:
            bc = hexagrams[hex_id]["binary_code"]
            binary_codes.append((int(hex_id), binary_to_tuple(bc)))
        
        # Check uniqueness
        seen = {}
        duplicates = []
        for hex_id, bc in binary_codes:
            if bc in seen:
                duplicates.append((hex_id, seen[bc]))
            else:
                seen[bc] = hex_id
        
        assert len(seen) == 64, (
            f"Expected 64 unique binary codes, got {len(seen)}. "
            f"Duplicates: {duplicates}"
        )


class TestTrigramConsistency:
    """Test that trigrams match binary code composition."""

    def test_trigram_matches_binary(self):
        """upper_trigram and lower_trigram should match binary_code composition.
        
        Binary format: [lower_bit1, lower_bit2, lower_bit3, upper_bit1, upper_bit2, upper_bit3]
        """
        hexagrams = load_hexagrams()
        
        mismatches = []
        for hex_id in hexagrams:
            hex_data = hexagrams[hex_id]
            bc = hex_data["binary_code"]
            declared_upper = hex_data["upper_trigram"]
            declared_lower = hex_data["lower_trigram"]
            
            # Calculate expected trigrams from binary
            expected_upper, expected_lower = trigram_from_binary(bc)
            
            if declared_upper != expected_upper or declared_lower != expected_lower:
                mismatches.append({
                    "hex_id": hex_id,
                    "binary": bc,
                    "declared": (declared_upper, declared_lower),
                    "expected": (expected_upper, expected_lower),
                })
        
        assert len(mismatches) == 0, (
            f"Found {len(mismatches)} hexagrams with trigram/binary mismatches: "
            f"{mismatches[:5]}..."
        )


class TestSpecificKnownCorruptions:
    """Test specific hexagram data correctness."""

    def test_hexagram_64_binary(self):
        """未济 should be 离上坎下 = [0,1,0,1,0,1].
        
        Verifies correct binary code for hexagram 64 (未济).
        """
        hexagrams = load_hexagrams()
        hex_64 = hexagrams["64"]
        
        expected_binary = [0, 1, 0, 1, 0, 1]  # 离上坎下
        assert hex_64["binary_code"] == expected_binary, (
            f"Hexagram 64 binary should be {expected_binary} (离上坎下), "
            f"got {hex_64['binary_code']}"
        )

    def test_hexagram_64_trigrams(self):
        """未济 should have upper_trigram=离 and lower_trigram=坎.
        
        Verifies correct trigrams for hexagram 64 (未济).
        """
        hexagrams = load_hexagrams()
        hex_64 = hexagrams["64"]
        
        assert hex_64["upper_trigram"] == "离", (
            f"Hexagram 64 upper_trigram should be '离', got '{hex_64['upper_trigram']}'"
        )
        assert hex_64["lower_trigram"] == "坎", (
            f"Hexagram 64 lower_trigram should be '坎', got '{hex_64['lower_trigram']}'"
        )


class TestReferenceAlignment:
    """Test that hexagrams.json matches the reference data."""

    def test_binary_matches_reference(self):
        """Each hexagram's binary_code should match the reference."""
        hexagrams = load_hexagrams()
        reference = load_reference()
        
        mismatches = []
        for hex_id in reference:
            current = hexagrams[hex_id]["binary_code"]
            expected = reference[hex_id]["binary_code"]
            
            if current != expected:
                mismatches.append({
                    "hex_id": hex_id,
                    "current": current,
                    "expected": expected,
                })
        
        assert len(mismatches) == 0, (
            f"Found {len(mismatches)} hexagrams with incorrect binary codes: "
            f"{mismatches[:5]}..."
        )

    def test_trigrams_match_reference(self):
        """Each hexagram's trigrams should match the reference."""
        hexagrams = load_hexagrams()
        reference = load_reference()
        
        mismatches = []
        for hex_id in reference:
            current_upper = hexagrams[hex_id]["upper_trigram"]
            current_lower = hexagrams[hex_id]["lower_trigram"]
            expected_upper = reference[hex_id]["upper_trigram"]
            expected_lower = reference[hex_id]["lower_trigram"]
            
            if current_upper != expected_upper or current_lower != expected_lower:
                mismatches.append({
                    "hex_id": hex_id,
                    "current": (current_upper, current_lower),
                    "expected": (expected_upper, expected_lower),
                })
        
        assert len(mismatches) == 0, (
            f"Found {len(mismatches)} hexagrams with incorrect trigrams: "
            f"{mismatches[:5]}..."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
