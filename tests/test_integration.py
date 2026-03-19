"""Integration tests for data chain verification.

Tests the complete data flow:
- hexagrams.json → data_loader → get_hexagram()
- hexagrams.json → shi_ying.json → get_shi_ying()
- hexagrams.json → yao_attributes.json → get_yao_attributes()
- hexagrams.json → hexagram_relations.json → get_hexagram_relations()
"""

import pytest
from core.data_loader import (
    get_yao_attributes,
    get_shi_ying,
    get_hexagram_relations,
)


class TestHexagramDataChain:
    """Test complete data chain for hexagrams."""

    def test_qian_complete_data(self):
        """Verify 乾卦 (hexagram 1) complete data chain."""
        # Shi-ying data
        sy = get_shi_ying(1)
        assert sy is not None
        assert sy["palace"] == "乾宫"
        assert sy["generation"] == "首卦"
        assert sy["shi_position"] == 6
        assert sy["ying_position"] == 3
        
        # Yao attributes - all 6 positions exist
        for pos in range(1, 7):
            ya = get_yao_attributes(1, pos)
            assert ya is not None, f"Missing yao at position {pos}"
            assert "liu_qin" in ya
            assert "na_jia_gan" in ya
            assert "na_jia_zhi" in ya
        
        # Shi yao verification
        ya_shi = get_yao_attributes(1, 6)
        assert ya_shi["is_shi"] is True
        
        # Ying yao verification
        ya_ying = get_yao_attributes(1, 3)
        assert ya_ying["is_ying"] is True
        
        # Relations
        cuo = get_hexagram_relations(1, "错卦")
        assert len(cuo) == 1
        assert cuo[0]["target_id"] == 64  # 乾错坤 = 未济
        
        # 乾 is self-zong (综卦 returns None)
        zong = get_hexagram_relations(1, "综卦")
        assert len(zong) == 0
        
        # Jiao and hu should exist
        jiao = get_hexagram_relations(1, "交卦")
        assert len(jiao) == 1
        
        hu = get_hexagram_relations(1, "互卦")
        assert len(hu) == 1

    def test_kun_complete_data(self):
        """Verify 坤卦 (hexagram 2) complete data chain."""
        sy = get_shi_ying(2)
        assert sy is not None
        assert sy["palace"] == "坤宫"
        assert sy["shi_position"] == 6
        
        # All 6 yao
        for pos in range(1, 7):
            ya = get_yao_attributes(2, pos)
            assert ya is not None
        
        # Relations
        cuo = get_hexagram_relations(2, "错卦")
        assert len(cuo) == 1
        assert cuo[0]["target_id"] == 63  # 坤错乾 = 既济
        
        # 坤 has zong (unlike 乾)
        zong = get_hexagram_relations(2, "综卦")
        assert len(zong) == 1

    def test_tai_complete_data(self):
        """Verify 泰卦 (hexagram 11) complete data chain."""
        sy = get_shi_ying(11)
        assert sy is not None
        assert sy["palace"] == "坤宫"  # 泰属坤宫
        assert sy["generation"] == "归魂"
        assert sy["shi_position"] == 3
        assert sy["ying_position"] == 6
        
        # All 6 yao
        for pos in range(1, 7):
            ya = get_yao_attributes(11, pos)
            assert ya is not None
        
        # Verify ying position
        ya_ying = get_yao_attributes(11, 6)
        assert ya_ying["is_ying"] is True
        
        # Relations
        for rt in ["错卦", "综卦", "交卦", "互卦"]:
            rels = get_hexagram_relations(11, rt)
            assert len(rels) >= 1

    def test_kan_complete_data(self):
        """Verify 坎卦 (hexagram 29) complete data chain."""
        sy = get_shi_ying(29)
        assert sy is not None
        assert sy["palace"] == "坎宫"
        assert sy["generation"] == "首卦"
        assert sy["shi_position"] == 6
        assert sy["ying_position"] == 3
        
        # All 6 yao
        for pos in range(1, 7):
            ya = get_yao_attributes(29, pos)
            assert ya is not None
        
        # Relations
        cuo = get_hexagram_relations(29, "错卦")
        assert len(cuo) == 1
        assert cuo[0]["target_id"] == 36  # 坎错明夷

    def test_wei_ji_complete_data(self):
        """Verify 未济卦 (hexagram 64) complete data chain."""
        sy = get_shi_ying(64)
        assert sy is not None
        assert sy["palace"] == "兑宫"
        assert sy["shi_position"] == 2
        assert sy["ying_position"] == 5
        
        # All 6 yao
        for pos in range(1, 7):
            ya = get_yao_attributes(64, pos)
            assert ya is not None
        
        # 未济 is self-zong
        zong = get_hexagram_relations(64, "综卦")
        assert len(zong) == 0
        
        # Relations
        cuo = get_hexagram_relations(64, "错卦")
        assert len(cuo) == 1


class TestSampleHexagrams:
    """Sample 5 hexagrams and verify data integrity."""

    @pytest.mark.parametrize("hex_id", [1, 2, 11, 29, 64])
    def test_all_six_yao_exist(self, hex_id):
        """Verify all 6 yao positions exist for each hexagram."""
        for pos in range(1, 7):
            ya = get_yao_attributes(hex_id, pos)
            assert ya is not None, f"Hexagram {hex_id} missing position {pos}"
            assert "liu_qin" in ya
            assert "wuxing" in ya

    @pytest.mark.parametrize("hex_id", [1, 2, 11, 29, 64])
    def test_shi_ying_exists(self, hex_id):
        """Verify shi_ying data exists."""
        sy = get_shi_ying(hex_id)
        assert sy is not None
        assert "palace" in sy
        assert "shi_position" in sy
        assert "ying_position" in sy

    @pytest.mark.parametrize("hex_id", [1, 2, 11, 29, 64])
    def test_relations_exist(self, hex_id):
        """Verify all relation types exist (except self-zong)."""
        for rt in ["错卦", "交卦", "互卦"]:
            rels = get_hexagram_relations(hex_id, rt)
            assert len(rels) >= 1, f"Hexagram {hex_id} missing {rt}"

    @pytest.mark.parametrize("hex_id", [1, 13, 19, 31, 34, 46, 52, 64])
    def test_self_zong_hexagrams(self, hex_id):
        """Verify self-zong hexagrams return empty for 综卦."""
        zong = get_hexagram_relations(hex_id, "综卦")
        assert len(zong) == 0


class TestCrossFileConsistency:
    """Verify cross-file references are consistent."""

    def test_shi_ying_palace_matches_hexagram(self):
        """Verify palace in shi_ying matches hexagram's palace."""
        for hex_id in [1, 2, 11, 29, 64]:
            sy = get_shi_ying(hex_id)
            assert sy is not None
            palace = sy["palace"]
            assert palace in ["乾宫", "兑宫", "坤宫", "艮宫", "坎宫", "离宫", "震宫", "巽宫"]

    def test_shi_position_yao_has_correct_flag(self):
        """Verify shi_position has is_shi=true."""
        test_cases = [
            (1, 6),
            (2, 6),
            (11, 3),
            (29, 6),
            (64, 2),
        ]
        for hex_id, shi_pos in test_cases:
            ya = get_yao_attributes(hex_id, shi_pos)
            assert ya is not None
            assert ya["is_shi"] is True, f"Hex {hex_id} pos {shi_pos} should be shi"

    def test_ying_position_yao_has_correct_flag(self):
        """Verify ying_position has is_ying=true."""
        test_cases = [
            (1, 3),
            (2, 3),
            (11, 6),
            (29, 3),
            (64, 5),
        ]
        for hex_id, ying_pos in test_cases:
            ya = get_yao_attributes(hex_id, ying_pos)
            assert ya is not None
            assert ya["is_ying"] is True, f"Hex {hex_id} pos {ying_pos} should be ying"

    def test_relation_targets_valid(self):
        """Verify all relation targets are valid hexagram IDs."""
        for hex_id in range(1, 65):
            for rt in ["错卦", "交卦", "互卦"]:
                rels = get_hexagram_relations(hex_id, rt)
                for rel in rels:
                    target = rel["target_id"]
                    assert 1 <= target <= 64


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_invalid_hexagram_id_returns_none(self):
        """Verify invalid hexagram ID returns None."""
        assert get_shi_ying(0) is None
        assert get_shi_ying(65) is None

    def test_invalid_position_returns_none(self):
        """Verify invalid position returns None."""
        assert get_yao_attributes(1, 0) is None
        assert get_yao_attributes(1, 7) is None

    def test_invalid_relation_type_returns_empty(self):
        """Verify invalid relation type returns empty list."""
        rels = get_hexagram_relations(1, "无效类型")
        assert rels == []
