"""六爻数学计算模块 (Yao Math Module).

Functions for calculating yao (line) attributes in I Ching hexagram analysis.
包括: 纳甲、五行、六亲、世应位置等计算.
"""

import json
from pathlib import Path
from typing import Tuple


# Cache for palace data
_palace_data = None
_palace_lookup = None
_generation_lookup = None

# Cache for najia data
_najia_data = None


def _load_palace_data() -> dict:
    """Load palace reference data from JSON file."""
    global _palace_data, _palace_lookup, _generation_lookup
    
    if _palace_data is not None:
        return _palace_data
    
    ref_file = Path(__file__).parent.parent / "tests/fixtures/reference/palace_reference.json"
    with open(ref_file, "r", encoding="utf-8") as f:
        _palace_data = json.load(f)
    
    # Build lookup dictionaries (use first occurrence for duplicates)
    _palace_lookup = {}
    _generation_lookup = {}
    
    for palace_name, palace_info in _palace_data["palaces"].items():
        for member in palace_info["members"]:
            hex_id = member["hexagram_id"]
            # Only add if not already present (keep first occurrence)
            if hex_id not in _palace_lookup:
                _palace_lookup[hex_id] = palace_name
                _generation_lookup[hex_id] = member["generation"]
    
    return _palace_data


def get_palace(hexagram_id: int) -> str:
    """Get palace name for given hexagram ID."""
    if not 1 <= hexagram_id <= 64:
        raise ValueError(f"Hexagram ID must be 1-64, got {hexagram_id}")
    
    _load_palace_data()
    
    if hexagram_id not in _palace_lookup:
        raise ValueError(f"Hexagram ID {hexagram_id} not found in palace data")
    
    return _palace_lookup[hexagram_id]


def get_generation(hexagram_id: int) -> str:
    """Get generation type for given hexagram ID."""
    if not 1 <= hexagram_id <= 64:
        raise ValueError(f"Hexagram ID must be 1-64, got {hexagram_id}")
    
    _load_palace_data()
    
    if hexagram_id not in _generation_lookup:
        raise ValueError(f"Hexagram ID {hexagram_id} not found in palace data")
    
    return _generation_lookup[hexagram_id]


# Shi position lookup by generation type (for non-首卦)
SHI_BY_GENERATION = {
    "首卦": None,  # Special case - depends on palace
    "一世": 1,
    "二世": 2,
    "三世": 3,
    "四世": 4,
    "五世": 5,
    "游魂": 4,
    "归魂": 3,
}

# Shi position for 首卦 by palace
SHI_FOR_SHOU_GUA = {
    "乾宫": 6,
    "兑宫": 6,
    "坤宫": 3,
    "艮宫": 3,
    "坎宫": 6,
    "离宫": 6,
    "震宫": 1,
    "巽宫": 4,
}


def get_shi_position(hexagram_id: int, generation: str) -> int:
    """Get shi (世 - host) position based on hexagram and generation type."""
    if generation not in SHI_BY_GENERATION:
        raise ValueError(f"Invalid generation type: {generation}")
    
    # For 首卦, shi position depends on palace
    if generation == "首卦":
        palace = get_palace(hexagram_id)
        return SHI_FOR_SHOU_GUA[palace]
    
    return SHI_BY_GENERATION[generation]


def get_ying_position(shi_position: int) -> int:
    """Get ying (应 - response) position from shi position.
    
    The ying position is always 3 positions away from shi.
    Formula: ying = (shi + 2) % 6 + 1
    """
    if not 1 <= shi_position <= 6:
        raise ValueError(f"Shi position must be 1-6, got {shi_position}")
    
    return (shi_position + 2) % 6 + 1


def _load_najia_data() -> dict:
    """Load najia reference data from JSON file."""
    global _najia_data
    
    if _najia_data is not None:
        return _najia_data
    
    ref_file = Path(__file__).parent.parent / "tests/fixtures/reference/najia_reference.json"
    with open(ref_file, "r", encoding="utf-8") as f:
        _najia_data = json.load(f)
    
    return _najia_data


def get_na_jia(trigram: str, position: int, is_yang: bool) -> Tuple[str, str]:
    """Get na-jia (天干地支) stem-branch for given trigram and yao position.
    
    Args:
        trigram: Trigram name ("乾", "坤", "震", "坎", "艮", "巽", "离", "兑")
        position: Yao position (1-6, from bottom to top)
        is_yang: True if yao is yang (active), False if yin (passive)
    
    Returns:
        Tuple of (stem, branch) e.g., ("甲", "子")
    
    Raises:
        ValueError: If trigram or position is invalid.
    """
    if not 1 <= position <= 6:
        raise ValueError(f"Position must be 1-6, got {position}")
    
    najia_data = _load_najia_data()
    
    if trigram not in najia_data["trigrams"]:
        raise ValueError(f"Invalid trigram: {trigram}")
    
    trigram_data = najia_data["trigrams"][trigram]
    stem = trigram_data["stem"]
    branches = trigram_data["branches"]
    
    # Position is 1-6, list is 0-indexed
    branch = branches[position - 1]
    
    return (stem, branch)


# Wuxing from earthly branches
BRANCH_WUXING = {
    # 阳支 (yang branches)
    "子": "水", "寅": "木", "辰": "土", "午": "火", "申": "金", "戌": "土",
    # 阴支 (yin branches)
    "丑": "土", "卯": "木", "巳": "火", "未": "土", "酉": "金", "亥": "水",
}

def get_wuxing_from_branch(branch: str) -> str:
    """Get wuxing from earthly branch.
    
    Args:
        branch: Earthly branch ("子", "丑", "寅", etc.)
    
    Returns:
        Wuxing element ("木", "火", "土", "金", "水")
    
    Raises:
        ValueError: If branch is invalid.
    """
    if branch not in BRANCH_WUXING:
        raise ValueError(f"Invalid branch: {branch}")
    return BRANCH_WUXING[branch]


# Wuxing from heavenly stems
STEM_WUXING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# Wuxing cycle (相生): 木 → 火 → 土 → 金 → 水 → 木
WUXING_CYCLE = ["木", "火", "土", "金", "水"]

def get_wuxing(stem: str) -> str:
    """Get wuxing (five elements) from heavenly stem.
    
    Args:
        stem: Heavenly stem ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
    
    Returns:
        Wuxing element ("木", "火", "土", "金", "水")
    
    Raises:
        ValueError: If stem is invalid.
    """
    if stem not in STEM_WUXING:
        raise ValueError(f"Invalid stem: {stem}")
    return STEM_WUXING[stem]


def get_liu_qin(yao_wuxing: str, palace_wuxing: str) -> str:
    """Get liu-qin (六亲 - six relations) based on wuxing relationship.
    
    The six relations are determined by comparing yao's wuxing with palace's wuxing:
    - 同我 (same as palace): 兄弟
    - 生我 (yao generates palace): 父母
    - 我生 (palace generates yao): 子孙
    - 我克 (palace overcomes yao): 妻财
    - 克我 (yao overcomes palace): 官鬼
    
    Wuxing cycle (相生): 木 → 火 → 土 → 金 → 水 → 木
    
    Args:
        yao_wuxing: Wuxing of the yao line ("木", "火", "土", "金", "水")
        palace_wuxing: Wuxing of the palace/trigram
    
    Returns:
        Liu-qin relation ("父母", "兄弟", "子孙", "妻财", "官鬼")
    
    Raises:
        ValueError: If wuxing values are invalid.
    """
    if yao_wuxing not in WUXING_CYCLE or palace_wuxing not in WUXING_CYCLE:
        raise ValueError(f"Invalid wuxing: yao={yao_wuxing}, palace={palace_wuxing}")
    
    # Same element = 兄弟
    if yao_wuxing == palace_wuxing:
        return "兄弟"
    
    yao_idx = WUXING_CYCLE.index(yao_wuxing)
    palace_idx = WUXING_CYCLE.index(palace_wuxing)
    
    # Calculate forward distance: how far yao is after palace in cycle
    # forward = (yao - palace) mod 5
    forward = (yao_idx - palace_idx) % 5
    
    # Wuxing relationship (木→火→土→金→水循环):
    # forward = 1: palace generates yao (我生) → 子孙
    # forward = 2: palace overcomes yao (我克) → 妻财
    # forward = 3: yao overcomes palace (克我) → 官鬼
    # forward = 4: yao generates palace (生我) → 父母
    
    if forward == 1:
        return "子孙"  # palace generates yao
    elif forward == 2:
        return "妻财"  # palace overcomes yao
    elif forward == 3:
        return "官鬼"  # yao overcomes palace
    elif forward == 4:
        return "父母"  # yao generates palace
    else:
        raise ValueError(f"Invalid wuxing relationship")
