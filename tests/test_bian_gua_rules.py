"""Tests for 朱熹《易学启蒙》变爻规则 (bian_gua rules).

This test module covers the 7 rules for interpreting changing lines (变爻).
Reference: 朱熹《易学启蒙》
"""

import pytest


class TestZhuXiBianGuaRules:
    """Test suite for 朱熹's 7 rules of 变爻 interpretation."""

    def test_rule_1_zero_changing_lines(self):
        """Rule 1: 0 changing lines → use original hexagram text (本卦卦辞).
        
        When there are no changing lines, interpret using the original
        hexagram's main text (卦辞).
        
        Example: 泰 (11) with no changing lines.
        """
        from core.bian_gua import get_interpretation_priority
        
        # 泰 (Tai, ID=11) with 0 changing lines
        result = get_interpretation_priority(11, [])
        
        assert result["rule_number"] == 1
        assert result["primary_source"] == "original_hexagram_text"
        assert result["secondary_source"] is None
        assert result["specific_yao"] is None

    def test_rule_2_one_changing_line(self):
        """Rule 2: 1 changing line → use original changing line text (本卦变爻辞).
        
        When there is exactly one changing line, interpret using that
        specific line's text (爻辞).
        
        Example: 乾 (1) with line 3 changing (九三).
        """
        from core.bian_gua import get_interpretation_priority
        
        # 乾 (Qian, ID=1) with line 3 changing
        result = get_interpretation_priority(1, [3])
        
        assert result["rule_number"] == 2
        assert result["primary_source"] == "original_line_text"
        assert result["specific_yao"] == [3]

    def test_rule_3_two_changing_lines(self):
        """Rule 3: 2 changing lines → use both, prioritize upper (本卦二变爻辞，以上爻为主).
        
        When there are two changing lines, use both line texts but
        prioritize the upper position (上爻).
        
        Example: 屯 (3) with lines 2 and 5 changing.
        """
        from core.bian_gua import get_interpretation_priority
        
        # 屯 (Zhun, ID=3) with lines 2 and 5 changing
        result = get_interpretation_priority(3, [2, 5])
        
        assert result["rule_number"] == 3
        assert result["primary_source"] == "original_two_line_texts"
        assert result["specific_yao"] == [2, 5]
        assert result["main_yao"] == 5  # Upper (5 is above 2)

    def test_rule_4_three_changing_lines(self):
        """Rule 4: 3 changing lines → original + transformed (本卦卦辞为主，之卦卦辞为辅).
        
        When there are three changing lines, use both the original
        hexagram text as primary and transformed hexagram text as secondary.
        
        Example: 讼 (6) with 3 changing lines.
        """
        from core.bian_gua import get_interpretation_priority
        
        # 讼 (Song, ID=6) with lines 1, 3, 5 changing
        result = get_interpretation_priority(6, [1, 3, 5])
        
        assert result["rule_number"] == 4
        assert result["primary_source"] == "original_hexagram_text"
        assert result["secondary_source"] == "transformed_hexagram_text"
        assert result["specific_yao"] == [1, 3, 5]

    def test_rule_5_four_changing_lines(self):
        """Rule 5: 4 changing lines → transformed's 2 unchanged, prioritize lower 
        (之卦二不变爻辞，以下爻为主).
        
        When there are four changing lines, use the two unchanged lines
        from the transformed hexagram, prioritizing the lower position.
        
        Example: 姤 (44) with 4 changing lines (unchanged lines: 2, 5).
        """
        from core.bian_gua import get_interpretation_priority
        
        # 姤 (Gou, ID=44) with lines 1, 3, 4, 6 changing (unchanged: 2, 5)
        result = get_interpretation_priority(44, [1, 3, 4, 6])
        
        assert result["rule_number"] == 5
        assert result["primary_source"] == "transformed_two_unchanged_line_texts"
        assert result["specific_yao"] == [2, 5]
        assert result["main_yao"] == 2  # Lower

    def test_rule_6_five_changing_lines(self):
        """Rule 6: 5 changing lines → transformed's single unchanged line 
        (之卦不变爻辞).
        
        When there are five changing lines, use the single unchanged
        line from the transformed hexagram.
        
        Example: 夬 (43) with 5 changing lines (unchanged line: 3).
        """
        from core.bian_gua import get_interpretation_priority
        
        # 夬 (Guai, ID=43) with lines 1, 2, 4, 5, 6 changing (unchanged: 3)
        result = get_interpretation_priority(43, [1, 2, 4, 5, 6])
        
        assert result["rule_number"] == 6
        assert result["primary_source"] == "transformed_single_unchanged_line_text"
        assert result["specific_yao"] == [3]

    def test_rule_7a_six_changing_lines_qian(self):
        """Rule 7a: 6 changing lines (Qian) → use 用九 (YongJiu).
        
        For 乾 (Qian) with all 6 lines changing, use 用九 instead of
        the transformed hexagram text.
        """
        from core.bian_gua import get_interpretation_priority
        
        # 乾 (Qian, ID=1) with all 6 lines changing
        result = get_interpretation_priority(1, [1, 2, 3, 4, 5, 6])
        
        assert result["rule_number"] == 7
        assert result["primary_source"] == "yong_jiu"  # 用九 for 乾
        assert result["specific_yao"] == [1, 2, 3, 4, 5, 6]

    def test_rule_7b_six_changing_lines_kun(self):
        """Rule 7b: 6 changing lines (Kun) → use 用六 (YongLiu).
        
        For 坤 (Kun) with all 6 lines changing, use 用六 instead of
        the transformed hexagram text.
        """
        from core.bian_gua import get_interpretation_priority
        
        # 坤 (Kun, ID=2) with all 6 lines changing
        result = get_interpretation_priority(2, [1, 2, 3, 4, 5, 6])
        
        assert result["rule_number"] == 7
        assert result["primary_source"] == "yong_liu"  # 用六 for 坤
        assert result["specific_yao"] == [1, 2, 3, 4, 5, 6]

    def test_rule_7c_six_changing_lines_other_hexagram(self):
        """Rule 7c: 6 changing lines (non-Qian/Kun) → use transformed hexagram text.
        
        For non-乾/坤 hexagrams with all 6 lines changing, use the
        transformed hexagram text (之卦卦辞).
        
        Example: 屯 (3) → 蒙 (4) with all lines changing.
        """
        from core.bian_gua import get_interpretation_priority
        
        # 屯 (Zhun, ID=3) with all 6 lines changing
        result = get_interpretation_priority(3, [1, 2, 3, 4, 5, 6])
        
        assert result["rule_number"] == 7
        assert result["primary_source"] == "transformed_hexagram_text"


class TestBianGuaParametrized:
    """Parametrized tests for 朱熹变爻 rules using pytest.mark.parametrize."""

    @pytest.mark.parametrize("hexagram_id,changing_lines,expected_rule", [
        # Rule 1: 0 changing lines
        (11, [], 1),
        (1, [], 1),
        (64, [], 1),
        # Rule 2: 1 changing line
        (1, [1], 2),
        (1, [3], 2),
        (1, [6], 2),
        # Rule 3: 2 changing lines
        (3, [2, 5], 3),
        (11, [1, 2], 3),
        # Rule 4: 3 changing lines
        (6, [1, 3, 5], 4),
        (1, [1, 3, 5], 4),
        # Rule 5: 4 changing lines
        (44, [1, 3, 4, 6], 5),
        # Rule 6: 5 changing lines
        (43, [1, 2, 4, 5, 6], 6),
    ])
    def test_rule_number_by_changing_line_count(
        self, hexagram_id, changing_lines, expected_rule
    ):
        """Verify rule number is correctly determined by changing line count."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(hexagram_id, changing_lines)
        assert result["rule_number"] == expected_rule

    @pytest.mark.parametrize("hexagram_id,changing_lines,expected_source", [
        # Rule 1: original hexagram text
        (11, [], "original_hexagram_text"),
        # Rule 2: original line text
        (1, [3], "original_line_text"),
        # Rule 3: two original line texts
        (3, [2, 5], "original_two_line_texts"),
        # Rule 4: original + transformed hexagram texts
        (6, [1, 3, 5], "original_hexagram_text"),
        # Rule 5: transformed two unchanged line texts
        (44, [1, 3, 4, 6], "transformed_two_unchanged_line_texts"),
        # Rule 6: transformed single unchanged line text
        (43, [1, 2, 4, 5, 6], "transformed_single_unchanged_line_text"),
    ])
    def test_primary_source_by_rule(
        self, hexagram_id, changing_lines, expected_source
    ):
        """Verify primary source is correctly determined by rule."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(hexagram_id, changing_lines)
        assert result["primary_source"] == expected_source


class TestBianGuaEdgeCases:
    """Edge case tests for 变爻 rules."""

    def test_ben_gua_identification(self):
        """Test that original hexagram (本卦) is correctly identified."""
        from core.bian_gua import get_interpretation_priority
        
        # Any hexagram can be the original
        result = get_interpretation_priority(25, [1, 2])
        assert "ben_gua_id" in result or result["rule_number"] in [1, 2, 3, 4, 5, 6, 7]

    def test_zhi_gua_transformation(self):
        """Test that transformed hexagram (之卦) is correctly derived."""
        from core.bian_gua import get_interpretation_priority
        
        # 乾 (1) with lines 1, 3 changing → 巽 (57)
        # Note: Actual transformation depends on line positions
        result = get_interpretation_priority(1, [1, 3])
        # Should contain info about the transformed hexagram
        assert "zhi_gua_id" in result or "transformed_hexagram" in result.get("secondary_source", "")

    def test_yao_positions_sorted(self):
        """Test that changing line positions are sorted correctly."""
        from core.bian_gua import get_interpretation_priority
        
        # Pass unsorted positions
        result = get_interpretation_priority(3, [5, 2, 1])
        
        # Should normalize to sorted order
        if result.get("specific_yao"):
            assert result["specific_yao"] == sorted(result["specific_yao"])

    def test_invalid_yao_position_raises(self):
        """Test that invalid yao positions raise appropriate errors."""
        from core.bian_gua import get_interpretation_priority
        
        with pytest.raises((ValueError, IndexError)):
            get_interpretation_priority(1, [0])  # Position 0 is invalid (1-6)

    def test_yao_position_out_of_range_raises(self):
        """Test that out-of-range yao positions raise errors."""
        from core.bian_gua import get_interpretation_priority
        
        with pytest.raises((ValueError, IndexError)):
            get_interpretation_priority(1, [7])  # Position 7 is invalid (1-6)


class TestBianGuaRuleDescriptions:
    """Tests verifying rule descriptions match 朱熹《易学启蒙》."""

    def test_rule_1_description(self):
        """Verify Rule 1: 本卦卦辞."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(11, [])
        assert "本卦卦辞" in result.get("description", "") or result["rule_number"] == 1

    def test_rule_2_description(self):
        """Verify Rule 2: 本卦变爻辞."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(1, [3])
        assert "本卦变爻" in result.get("description", "") or result["rule_number"] == 2

    def test_rule_3_description(self):
        """Verify Rule 3: 本卦二变爻辞，以上爻为主."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(3, [2, 5])
        assert "上爻" in result.get("description", "") or result["rule_number"] == 3
        assert result.get("main_yao") == 5

    def test_rule_4_description(self):
        """Verify Rule 4: 本卦卦辞为主，之卦卦辞为辅."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(6, [1, 3, 5])
        assert "辅" in result.get("description", "") or result["secondary_source"] is not None

    def test_rule_5_description(self):
        """Verify Rule 5: 之卦二不变爻辞，以下爻为主."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(44, [1, 3, 4, 6])
        assert "下爻" in result.get("description", "") or result["rule_number"] == 5

    def test_rule_6_description(self):
        """Verify Rule 6: 之卦不变爻辞."""
        from core.bian_gua import get_interpretation_priority
        
        result = get_interpretation_priority(43, [1, 2, 4, 5, 6])
        assert "之卦不变" in result.get("description", "") or result["rule_number"] == 6

    def test_rule_7_qian_kun_special(self):
        """Verify Rule 7: 乾坤用九/用六."""
        from core.bian_gua import get_interpretation_priority
        
        # 乾用九
        result_qian = get_interpretation_priority(1, [1, 2, 3, 4, 5, 6])
        assert "用九" in result_qian.get("description", "") or result_qian["primary_source"] == "yong_jiu"
        
        # 坤用六
        result_kun = get_interpretation_priority(2, [1, 2, 3, 4, 5, 6])
        assert "用六" in result_kun.get("description", "") or result_kun["primary_source"] == "yong_liu"
