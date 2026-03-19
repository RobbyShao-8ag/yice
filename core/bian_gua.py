"""朱熹《易学启蒙》变爻规则 (bian_gua rules).

This module implements the 7 rules for interpreting changing lines (变爻).
Reference: 朱熹《易学启蒙》

Rules:
1. 六爻皆不变 → 占本卦卦辞
2. 一爻变 → 占本卦变爻爻辞  
3. 二爻变 → 占本卦二变爻爻辞，以上爻为主
4. 三爻变 → 占本卦及之卦卦辞，以本卦为主
5. 四爻变 → 占之卦二不变爻爻辞，以下爻为主
6. 五爻变 → 占之卦不变爻爻辞
7. 六爻变 → 乾坤占二用，余卦占之卦卦辞
"""

import json
from pathlib import Path
from typing import Any

# Cache for hexagrams data
_hexagrams_data = None
_lines_data = None

# Hardcoded texts for 乾/坤 special cases
YONG_JIU_TEXT = "用九：见群龙无首，吉。"
YONG_LIU_TEXT = "用六：利永贞。"


def _load_hexagrams() -> dict:
    """Load hexagrams data from JSON."""
    global _hexagrams_data
    
    if _hexagrams_data is not None:
        return _hexagrams_data
    
    data_file = Path(__file__).parent.parent / "data/hexagrams.json"
    with open(data_file, "r", encoding="utf-8") as f:
        _hexagrams_data = json.load(f)
    
    return _hexagrams_data


def _load_lines() -> list[dict]:
    """Load lines data from JSON."""
    global _lines_data
    
    if _lines_data is not None:
        return _lines_data
    
    data_file = Path(__file__).parent.parent / "data/lines.json"
    with open(data_file, "r", encoding="utf-8") as f:
        _lines_data = json.load(f)
    
    return _lines_data


def get_interpretation_priority(
    ben_gua_id: int,
    bian_yao_positions: list[int]
) -> dict[str, Any]:
    """
    Determine interpretation priority based on 朱熹's 7 rules.
    
    Args:
        ben_gua_id: Original hexagram ID (1-64)
        bian_yao_positions: Changing line positions [1,2,3,4,5,6]
        
    Returns:
        dict with:
        - rule_number: 1-7
        - primary_source: which text to use
        - secondary_source: optional secondary text
        - specific_yao: which line(s) to read
        - main_yao: priority line for rules 3, 5
        - description: rule description
        - zhi_gua_id: transformed hexagram ID (for rules 4,5,6,7)
        - ben_gua_id: original hexagram ID
        
    Raises:
        ValueError: If ben_gua_id out of range or bian_yao_positions invalid
    """
    # Input validation
    if not isinstance(ben_gua_id, int) or ben_gua_id < 1 or ben_gua_id > 64:
        raise ValueError(f"ben_gua_id must be 1-64, got {ben_gua_id}")
    
    if not bian_yao_positions:
        bian_yao_positions = []
    else:
        # Validate positions
        for pos in bian_yao_positions:
            if not isinstance(pos, int) or pos < 1 or pos > 6:
                raise ValueError(f"bian_yao_positions must be 1-6, got {pos}")
        # Sort positions
        bian_yao_positions = sorted(bian_yao_positions)
    
    num_changing = len(bian_yao_positions)
    
    # All valid yao positions (1-6)
    all_positions = [1, 2, 3, 4, 5, 6]
    
    # Calculate unchanged positions
    unchanged_positions = [p for p in all_positions if p not in bian_yao_positions]
    
    # Calculate zhi_gua_id for all rules (for potential use in any rule)
    zhi_gua_id = _calculate_zhi_gua_id(ben_gua_id, bian_yao_positions)
    
    # Base result with ben_gua_id
    result: dict[str, Any] = {
        "ben_gua_id": ben_gua_id,
    }
    
    # Rule selection based on number of changing lines
    if num_changing == 0:
        # Rule 1: 六爻皆不变 → 占本卦卦辞
        result.update({
            "rule_number": 1,
            "primary_source": "original_hexagram_text",
            "secondary_source": None,
            "specific_yao": None,
            "main_yao": None,
            "description": "六爻皆不变，占本卦卦辞",
            "zhi_gua_id": zhi_gua_id,  # Include for completeness
        })
        
    elif num_changing == 1:
        # Rule 2: 一爻变 → 占本卦变爻爻辞
        result.update({
            "rule_number": 2,
            "primary_source": "original_line_text",
            "secondary_source": None,
            "specific_yao": bian_yao_positions,
            "main_yao": None,
            "description": "一爻变，占本卦变爻爻辞",
            "zhi_gua_id": zhi_gua_id,  # Include for completeness
        })
        
    elif num_changing == 2:
        # Rule 3: 二爻变 → 占本卦二变爻爻辞，以上爻为主
        main_yao = max(bian_yao_positions)  # Upper position has higher number
        result.update({
            "rule_number": 3,
            "primary_source": "original_two_line_texts",
            "secondary_source": None,
            "specific_yao": bian_yao_positions,
            "main_yao": main_yao,
            "description": "二爻变，占本卦二变爻爻辞，以上爻为主",
            "zhi_gua_id": zhi_gua_id,  # Include for completeness
        })
        
    elif num_changing == 3:
        # Rule 4: 三爻变 → 占本卦及之卦卦辞，以本卦为主
        result.update({
            "rule_number": 4,
            "primary_source": "original_hexagram_text",
            "secondary_source": "transformed_hexagram_text",
            "specific_yao": bian_yao_positions,
            "main_yao": None,
            "description": "三爻变，占本卦及之卦卦辞，以本卦为主",
            "zhi_gua_id": zhi_gua_id,
        })
        
    elif num_changing == 4:
        # Rule 5: 四爻变 → 占之卦二不变爻爻辞，以下爻为主
        main_yao = min(unchanged_positions)  # Lower position has smaller number
        result.update({
            "rule_number": 5,
            "primary_source": "transformed_two_unchanged_line_texts",
            "specific_yao": unchanged_positions,
            "main_yao": main_yao,
            "description": "四爻变，占之卦二不变爻爻辞，以下爻为主",
            "zhi_gua_id": zhi_gua_id,
        })
        
    elif num_changing == 5:
        # Rule 6: 五爻变 → 占之卦不变爻爻辞
        result.update({
            "rule_number": 6,
            "primary_source": "transformed_single_unchanged_line_text",
            "specific_yao": unchanged_positions,
            "main_yao": None,
            "description": "五爻变，占之卦不变爻爻辞",
            "zhi_gua_id": zhi_gua_id,
        })
        
    else:  # num_changing == 6
        # Rule 7: 六爻变 → 乾坤占二用，余卦占之卦卦辞
        if ben_gua_id == 1:  # 乾卦
            result.update({
                "rule_number": 7,
                "primary_source": "yong_jiu",
                "secondary_source": None,
                "specific_yao": [1, 2, 3, 4, 5, 6],
                "main_yao": None,
                "description": "六爻变，乾卦用九",
                "special_case": "qian",
                "zhi_gua_id": zhi_gua_id,
            })
        elif ben_gua_id == 2:  # 坤卦
            result.update({
                "rule_number": 7,
                "primary_source": "yong_liu",
                "secondary_source": None,
                "specific_yao": [1, 2, 3, 4, 5, 6],
                "main_yao": None,
                "description": "六爻变，坤卦用六",
                "special_case": "kun",
                "zhi_gua_id": zhi_gua_id,
            })
        else:
            result.update({
                "rule_number": 7,
                "primary_source": "transformed_hexagram_text",
                "secondary_source": None,
                "specific_yao": None,
                "main_yao": None,
                "description": "六爻变，占之卦卦辞",
                "zhi_gua_id": zhi_gua_id,
            })
    
    return result


def _calculate_zhi_gua_id(ben_gua_id: int, bian_yao_positions: list[int]) -> int:
    """
    Calculate the transformed hexagram (之卦) ID.
    
    Args:
        ben_gua_id: Original hexagram ID (1-64)
        bian_yao_positions: Changing line positions
        
    Returns:
        Transformed hexagram ID
    """
    # Get original hexagram binary code
    hexagrams = _load_hexagrams()
    hexagram = hexagrams[str(ben_gua_id)]
    binary_code = list(hexagram["binary_code"])
    
    # The binary_code is stored as [position1, position2, ..., position6]
    # where position1 is the bottom (初爻) and position6 is the top (上爻)
    # Flip the changing lines (yang becomes yin, yin becomes yang)
    for pos in bian_yao_positions:
        # Position is 1-indexed, list is 0-indexed
        idx = pos - 1
        binary_code[idx] = 1 - binary_code[idx]
    
    # Calculate new hexagram ID from binary code
    # Binary code format: [lower_yao, ..., upper_yao] where 1=yang, 0=yin
    # Trigram calculation: bottom 3 lines = lower trigram, top 3 lines = upper trigram
    # lower_trigram = positions 1,2,3 (indices 0,1,2)
    # upper_trigram = positions 4,5,6 (indices 3,4,5)
    lower_trigram = _binary_to_trigram(binary_code[0:3])   # 下卦
    upper_trigram = _binary_to_trigram(binary_code[3:6])   # 上卦
    
    # Hexagram ID: (7-upper_trigram) * 8 + (7-lower_trigram) + 1
    zhi_gua_id = (7 - upper_trigram) * 8 + (7 - lower_trigram) + 1
    
    return zhi_gua_id


def _binary_to_trigram(binary: list[int]) -> int:
    """
    Convert 3-line trigram binary to trigram value.
    
    Args:
        binary: List of 3 integers (0 or 1), bottom to top
        
    Returns:
        Trigram value 0-7
    """
    # Binary: [bottom, middle, top] -> value
    # 111 -> 7 (乾), 000 -> 0 (坤)
    value = binary[0] * 4 + binary[1] * 2 + binary[2]
    return value


def select_interpretation_text(
    ben_gua_id: int,
    bian_yao_positions: list[int]
) -> dict[str, Any]:
    """
    Select the appropriate interpretation text based on 朱熹's 7 rules.
    
    Args:
        ben_gua_id: Original hexagram ID (1-64)
        bian_yao_positions: Changing line positions [1,2,3,4,5,6]
        
    Returns:
        dict with:
        - text_type: "hexagram_text", "line_text", "yong_jiu", "yong_liu"
        - hexagram_id: Which hexagram's text to use
        - line_position: Which line (1-6), or None for hexagram text
        - text_preview: First 20 chars of the text
        - full_text: Complete text
        - rule_number: 朱熹 rule 1-7
        
    Raises:
        ValueError: If ben_gua_id out of range or bian_yao_positions invalid
    """
    # Get interpretation priority
    priority = get_interpretation_priority(ben_gua_id, bian_yao_positions)
    
    rule_number = priority["rule_number"]
    primary_source = priority["primary_source"]
    
    # Initialize result
    result: dict[str, Any] = {
        "rule_number": rule_number,
    }
    
    # Handle special cases for yong_jiu and yong_liu
    if primary_source == "yong_jiu":
        result["text_type"] = "yong_jiu"
        result["hexagram_id"] = ben_gua_id
        result["line_position"] = None
        result["full_text"] = YONG_JIU_TEXT
        result["text_preview"] = YONG_JIU_TEXT[:20]
        return result
    
    if primary_source == "yong_liu":
        result["text_type"] = "yong_liu"
        result["hexagram_id"] = ben_gua_id
        result["line_position"] = None
        result["full_text"] = YONG_LIU_TEXT
        result["text_preview"] = YONG_LIU_TEXT[:20]
        return result
    
    # Load data
    hexagrams = _load_hexagrams()
    lines = _load_lines()
    
    # Determine which text to fetch based on rule
    if primary_source == "original_hexagram_text":
        # Rule 1 or Rule 4 primary
        result["text_type"] = "hexagram_text"
        result["hexagram_id"] = ben_gua_id
        result["line_position"] = None
        full_text = hexagrams[str(ben_gua_id)]["gua_ci"]
        result["full_text"] = full_text
        result["text_preview"] = full_text[:20] if full_text else ""
        
    elif primary_source == "original_line_text":
        # Rule 2: single changing line from original hexagram
        result["text_type"] = "line_text"
        result["hexagram_id"] = ben_gua_id
        position = priority["specific_yao"][0]  # Single position
        result["line_position"] = position
        full_text = _get_line_text(lines, ben_gua_id, position)
        result["full_text"] = full_text
        result["text_preview"] = full_text[:20] if full_text else ""
        
    elif primary_source == "original_two_line_texts":
        # Rule 3: two changing lines from original hexagram
        result["text_type"] = "line_text"
        result["hexagram_id"] = ben_gua_id
        positions = priority["specific_yao"]  # Two positions
        result["line_position"] = positions[0]  # Primary is the first one
        # Get both texts, but primary is the main_yao (upper)
        full_text = _get_line_text(lines, ben_gua_id, priority["main_yao"])
        result["full_text"] = full_text
        result["text_preview"] = full_text[:20] if full_text else ""
        
    elif primary_source == "transformed_hexagram_text":
        # Rule 4 secondary, or Rule 7 for non-Qian/Kun
        result["text_type"] = "hexagram_text"
        result["hexagram_id"] = priority["zhi_gua_id"]
        result["line_position"] = None
        full_text = hexagrams[str(priority["zhi_gua_id"])]["gua_ci"]
        result["full_text"] = full_text
        result["text_preview"] = full_text[:20] if full_text else ""
        
    elif primary_source == "transformed_two_unchanged_line_texts":
        # Rule 5: two unchanged lines from transformed hexagram
        result["text_type"] = "line_text"
        result["hexagram_id"] = priority["zhi_gua_id"]
        positions = priority["specific_yao"]  # Two positions
        result["line_position"] = positions[0]  # Primary is the first one (lower)
        full_text = _get_line_text(lines, priority["zhi_gua_id"], priority["main_yao"])
        result["full_text"] = full_text
        result["text_preview"] = full_text[:20] if full_text else ""
        
    elif primary_source == "transformed_single_unchanged_line_text":
        # Rule 6: single unchanged line from transformed hexagram
        result["text_type"] = "line_text"
        result["hexagram_id"] = priority["zhi_gua_id"]
        position = priority["specific_yao"][0]  # Single position
        result["line_position"] = position
        full_text = _get_line_text(lines, priority["zhi_gua_id"], position)
        result["full_text"] = full_text
        result["text_preview"] = full_text[:20] if full_text else ""
    
    return result


def _get_line_text(lines: list[dict], hexagram_id: int, position: int) -> str:
    """
    Get the line text for a specific hexagram and position.
    
    Args:
        lines: List of line data
        hexagram_id: Hexagram ID (1-64)
        position: Line position (1-6)
        
    Returns:
        Line text or empty string if not found
    """
    for line in lines:
        if line.get("hexagram_id") == hexagram_id and line.get("position") == position:
            return line.get("text", "")
    return ""
