"""六兽 (Liu Shou / Six Beasts) allocation module.

This module provides functions for allocating six beasts based on day stem (日干)
and retrieving their meanings.

Reference: 梅花易数六兽配日干

六兽: 青龙, 朱雀, 勾陈, 螣蛇, 白虎, 玄武
"""

from typing import Any

# 六兽配日干 mapping
# Order: 初爻 -> 二爻 -> 三爻 -> 四爻 -> 五爻 -> 上爻
LIU_SHOU_BY_DAY_STEM: dict[str, list[str]] = {
    "甲": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
    "乙": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
    "丙": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
    "丁": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
    "戊": ["勾陈", "螣蛇", "白虎", "玄武", "青龙", "朱雀"],
    "己": ["勾陈", "螣蛇", "白虎", "玄武", "青龙", "朱雀"],
    "庚": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
    "辛": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
    "壬": ["玄武", "青龙", "朱雀", "勾陈", "螣蛇", "白虎"],
    "癸": ["玄武", "青龙", "朱雀", "勾陈", "螣蛇", "白虎"],
}

# 六兽含义 mapping
LIU_SHOU_MEANINGS: dict[str, dict[str, str]] = {
    "青龙": {"属性": "吉神", "象征": "喜庆、财富、婚姻", "五行": "木"},
    "朱雀": {"属性": "凶神", "象征": "文书、口舌、信息", "五行": "火"},
    "勾陈": {"属性": "凶神", "象征": "田土、牢狱、迟滞", "五行": "土"},
    "螣蛇": {"属性": "凶神", "象征": "惊恐、怪异、虚惊", "五行": "土"},
    "白虎": {"属性": "凶神", "象征": "血光、丧事、凶险", "五行": "金"},
    "玄武": {"属性": "凶神", "象征": "盗贼、暗昧、欺诈", "五行": "水"},
}


def allocate_six_beasts(day_stem: str) -> list[str]:
    """Allocate six beasts based on day stem.

    Args:
        day_stem: One of 甲乙丙丁戊己庚辛壬癸

    Returns:
        List of 6 beasts from 初爻 (index 0) to 上爻 (index 5)

    Raises:
        ValueError: If day_stem is invalid
    """
    if day_stem not in LIU_SHOU_BY_DAY_STEM:
        raise ValueError(f"Invalid day stem: {day_stem}. Must be one of 甲乙丙丁戊己庚辛壬癸")
    
    return LIU_SHOU_BY_DAY_STEM[day_stem]


def get_liu_shou_meaning(beast: str) -> dict[str, str]:
    """Get meaning of a six beast.

    Args:
        beast: One of 青龙, 朱雀, 勾陈, 螣蛇, 白虎, 玄武

    Returns:
        Dict with keys:
        - 属性: 吉神 or 凶神
        - 象征: symbolic meanings
        - 五行: five element

    Raises:
        ValueError: If beast is invalid
    """
    if beast not in LIU_SHOU_MEANINGS:
        raise ValueError(f"Invalid beast: {beast}. Must be one of 青龙, 朱雀, 勾陈, 螣蛇, 白虎, 玄武")
    
    return LIU_SHOU_MEANINGS[beast]
