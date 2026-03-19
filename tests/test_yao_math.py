"""Tests for yao_math module.

TDD approach: tests are written first, they will fail until implementation is complete.
"""

import pytest
from core.yao_math import (
    get_na_jia,
    get_wuxing,
    get_liu_qin,
    get_shi_position,
    get_ying_position,
)


class TestGetNaJia:
    """Tests for get_na_jia function."""
    
    def test_na_jia_qian_position_1(self):
        """乾初爻 should return 甲子."""
        result = get_na_jia("乾", 1, True)
        assert result == ("甲", "子")
    
    def test_na_jia_qian_position_2(self):
        """乾二爻 should return 甲寅."""
        result = get_na_jia("乾", 2, True)
        assert result == ("甲", "寅")
    
    def test_na_jia_kun_position_1(self):
        """坤初爻 should return 乙未."""
        result = get_na_jia("坤", 1, False)
        assert result == ("乙", "未")
    
    def test_na_jia_invalid_trigram(self):
        """Invalid trigram should raise ValueError."""
        with pytest.raises(ValueError):
            get_na_jia("无效", 1, True)
    
    def test_na_jia_invalid_position(self):
        """Invalid position should raise ValueError."""
        with pytest.raises(ValueError):
            get_na_jia("乾", 7, True)


class TestGetWuxing:
    """Tests for get_wuxing function."""
    
    def test_wuxing_jia(self):
        """甲 -> 木"""
        assert get_wuxing("甲") == "木"
    
    def test_wuxing_yi(self):
        """乙 -> 木"""
        assert get_wuxing("乙") == "木"
    
    def test_wuxing_bing(self):
        """丙 -> 火"""
        assert get_wuxing("丙") == "火"
    
    def test_wuxing_ding(self):
        """丁 -> 火"""
        assert get_wuxing("丁") == "火"
    
    def test_wuxing_wu(self):
        """戊 -> 土"""
        assert get_wuxing("戊") == "土"
    
    def test_wuxing_ji(self):
        """己 -> 土"""
        assert get_wuxing("己") == "土"
    
    def test_wuxing_geng(self):
        """庚 -> 金"""
        assert get_wuxing("庚") == "金"
    
    def test_wuxing_xin(self):
        """辛 -> 金"""
        assert get_wuxing("辛") == "金"
    
    def test_wuxing_ren(self):
        """壬 -> 水"""
        assert get_wuxing("壬") == "水"
    
    def test_wuxing_gui(self):
        """癸 -> 水"""
        assert get_wuxing("癸") == "水"
    
    def test_wuxing_invalid(self):
        """Invalid stem should raise ValueError."""
        with pytest.raises(ValueError):
            get_wuxing("无效")


class TestGetLiuQin:
    """Tests for get_liu_qin function."""
    
    def test_liu_qin_zi_sun_water_in_metal_palace(self):
        """水在金宫: 金生水 -> 子孙"""
        assert get_liu_qin("水", "金") == "子孙"
    
    def test_liu_qin_cai_fire_in_metal_palace(self):
        """火在金宫: 火克金 -> 官鬼"""
        assert get_liu_qin("火", "金") == "官鬼"
    
    def test_liu_qin_cai_wood_in_metal_palace(self):
        """木在金宫: 金克木 -> 妻财"""
        assert get_liu_qin("木", "金") == "妻财"
    
    def test_liu_qin_parents_water_in_fire_palace(self):
        """水在火宫: 火克水 -> 官鬼"""
        assert get_liu_qin("水", "火") == "官鬼"
    
    def test_liu_qin_brother_same_element(self):
        """同五行 -> 兄弟"""
        assert get_liu_qin("木", "木") == "兄弟"
        assert get_liu_qin("火", "火") == "兄弟"


class TestGetShiPosition:
    """Tests for get_shi_position function."""
    
    def test_shi_position_shou_gua_qian(self):
        """乾卦首卦: 世在六位 (position 6)"""
        assert get_shi_position(1, "首卦") == 6
    
    def test_shi_position_shou_gua_kun(self):
        """坤卦首卦: 世在三位 (position 3)"""
        assert get_shi_position(2, "首卦") == 3
    
    def test_shi_position_shou_gua_zhen(self):
        """震卦首卦: 世在一阳 (position 1)"""
        assert get_shi_position(51, "首卦") == 1
    
    def test_shi_position_you_hun(self):
        """游魂卦: 世在四位 (position 4)"""
        # 游魂卦 example: 晋 (35)
        assert get_shi_position(35, "游魂") == 4
    
    def test_shi_position_gui_hun(self):
        """归魂卦: 世在三位 (position 3)"""
        # 归魂卦 example: 师 (7)
        assert get_shi_position(7, "归魂") == 3
    
    def test_shi_position_invalid_generation(self):
        """Invalid generation type should raise ValueError."""
        with pytest.raises(ValueError):
            get_shi_position(1, "无效")


class TestGetYingPosition:
    """Tests for get_ying_position function."""
    
    def test_ying_position_from_6(self):
        """世在六位, 应在三位"""
        assert get_ying_position(6) == 3
    
    def test_ying_position_from_1(self):
        """世在一位, 应在四位"""
        assert get_ying_position(1) == 4
    
    def test_ying_position_from_2(self):
        """世在二位, 应在五位"""
        assert get_ying_position(2) == 5
    
    def test_ying_position_from_3(self):
        """世在三位, 应在六位"""
        assert get_ying_position(3) == 6
    
    def test_ying_position_from_4(self):
        """世在四位, 应在一位"""
        assert get_ying_position(4) == 1
    
    def test_ying_position_from_5(self):
        """世在五位, 应在二位"""
        assert get_ying_position(5) == 2
    
    def test_ying_position_invalid(self):
        """Invalid position should raise ValueError."""
        with pytest.raises(ValueError):
            get_ying_position(0)
        with pytest.raises(ValueError):
            get_ying_position(7)


import json
from pathlib import Path


def load_json(filepath: str) -> list:
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


class TestYaoAttributes:
    """Tests for yao_attributes.json data."""
    
    def test_yao_attributes_count(self):
        """Verify exactly 384 records (64 × 6)."""
        ya = load_json("data/yao_attributes.json")
        assert len(ya) == 384, f"Expected 384, got {len(ya)}"
    
    def test_yao_attributes_schema(self):
        """Verify all required fields present."""
        ya = load_json("data/yao_attributes.json")
        
        required_fields = [
            "line_id", "hexagram_id", "position",
            "na_jia_gan", "na_jia_zhi", "wuxing", "liu_qin",
            "is_shi", "is_ying", "is_fei", "is_fu"
        ]
        
        for record in ya[:5]:  # Check first 5
            for field in required_fields:
                assert field in record, f"Missing field: {field}"
    
    def test_qian_shi_yao(self):
        """Verify 乾卦世爻 (position 6) has correct attributes."""
        ya = load_json("data/yao_attributes.json")
        
        qian_6 = next((x for x in ya if x["line_id"] == "1-6"), None)
        assert qian_6 is not None
        assert qian_6["is_shi"] == True, "Qian position 6 should be shi"
        assert qian_6["na_jia_gan"] == "甲"
        assert qian_6["na_jia_zhi"] == "戌"
    
    def test_qian_ying_yao(self):
        """Verify 乾卦应爻 (position 3) has correct attributes."""
        ya = load_json("data/yao_attributes.json")
        
        qian_3 = next((x for x in ya if x["line_id"] == "1-3"), None)
        assert qian_3 is not None
        assert qian_3["is_ying"] == True, "Qian position 3 should be ying"
    
    def test_na_jia_qian(self):
        """Verify 乾卦六爻纳甲."""
        ya = load_json("data/yao_attributes.json")
        
        expected = {
            "1-1": ("甲", "子"),
            "1-2": ("甲", "寅"),
            "1-3": ("甲", "辰"),
            "1-4": ("甲", "午"),
            "1-5": ("甲", "申"),
            "1-6": ("甲", "戌"),
        }
        
        for pos in range(1, 7):
            record = next((x for x in ya if x["line_id"] == f"1-{pos}"), None)
            assert record is not None
            assert (record["na_jia_gan"], record["na_jia_zhi"]) == expected[f"1-{pos}"]
    
    def test_na_jia_kun(self):
        """Verify 坤卦六爻纳甲."""
        ya = load_json("data/yao_attributes.json")
        
        expected = {
            "2-1": ("乙", "未"),
            "2-2": ("乙", "巳"),
            "2-3": ("乙", "卯"),
            "2-4": ("乙", "丑"),
            "2-5": ("乙", "亥"),
            "2-6": ("乙", "酉"),
        }
        
        for pos in range(1, 7):
            record = next((x for x in ya if x["line_id"] == f"2-{pos}"), None)
            assert record is not None
            assert (record["na_jia_gan"], record["na_jia_zhi"]) == expected[f"2-{pos}"]
    
    def test_liu_qin_calculations(self):
        """Verify liu_qin calculations for various wuxing."""
        ya = load_json("data/yao_attributes.json")
        
        # 乾卦 position 5 is 兄弟 (same as palace 金)
        qian_5 = next((x for x in ya if x["line_id"] == "1-5"), None)
        assert qian_5["liu_qin"] == "兄弟", f"Expected 兄弟, got {qian_5['liu_qin']}"
        
        # 乾卦 position 6 is 父母 (土生金)
        qian_6 = next((x for x in ya if x["line_id"] == "1-6"), None)
        assert qian_6["liu_qin"] == "父母", f"Expected 父母, got {qian_6['liu_qin']}"
    
    def test_sample_hexagrams(self):
        """Verify sample 10 hexagrams have complete data."""
        ya = load_json("data/yao_attributes.json")
        
        sample_ids = [1, 2, 11, 29, 30, 51, 57, 52, 58, 64]
        
        for hex_id in sample_ids:
            # All 6 positions should exist
            positions = [x for x in ya if x["hexagram_id"] == hex_id]
            assert len(positions) == 6, f"Hexagram {hex_id} should have 6 positions"
            
            # Each should have required fields
            for p in positions:
                assert p["na_jia_gan"] is not None
                assert p["na_jia_zhi"] is not None
                assert p["wuxing"] is not None
                assert p["liu_qin"] is not None
    
    def test_shi_ying_positions(self):
        """Verify shi/ying positions match expected."""
        ya = load_json("data/yao_attributes.json")
        
        # Check: exactly one shi and one ying per hexagram
        for hex_id in range(1, 65):
            positions = [x for x in ya if x["hexagram_id"] == hex_id]
            shi_count = sum(1 for p in positions if p["is_shi"])
            ying_count = sum(1 for p in positions if p["is_ying"])
            
            assert shi_count == 1, f"Hexagram {hex_id} should have exactly 1 shi"
            assert ying_count == 1, f"Hexagram {hex_id} should have exactly 1 ying"
    
    def test_wuxing_values(self):
        """Verify wuxing values are valid."""
        ya = load_json("data/yao_attributes.json")
        
        valid_wuxing = {"木", "火", "土", "金", "水"}
        
        for record in ya:
            assert record["wuxing"] in valid_wuxing, f"Invalid wuxing: {record['wuxing']}"
    
    def test_liu_qin_values(self):
        """Verify liu_qin values are valid."""
        ya = load_json("data/yao_attributes.json")
        
        valid_liu_qin = {"父母", "兄弟", "子孙", "妻财", "官鬼"}
        
        for record in ya:
            assert record["liu_qin"] in valid_liu_qin, f"Invalid liu_qin: {record['liu_qin']}"
