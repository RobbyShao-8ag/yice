"""Tests for hu_gua calculation module."""

from core.hu_gua import calculate_hu_gua


def test_qian_hu_gua():
    """Test: 乾为天 (Qian) mutual hexagram is itself.

    All yang lines: [1,1,1,1,1,1]
    Lower trigram (二三四): [1,1,1] -> 乾
    Upper trigram (三四五): [1,1,1] -> 乾
    Result: 乾为天 (ID=1)
    """
    result = calculate_hu_gua(1, [1, 1, 1, 1, 1, 1])
    assert result == 1


def test_kun_hu_gua():
    """Test: 坤为地 (Kun) mutual hexagram is itself.

    All yin lines: [0,0,0,0,0,0]
    Lower trigram (二三四): [0,0,0] -> 坤
    Upper trigram (三四五): [0,0,0] -> 坤
    Result: 坤为地 (ID=64)
    """
    result = calculate_hu_gua(64, [0, 0, 0, 0, 0, 0])
    assert result == 64


def test_xun_qian_hu_gua():
    """Test: 巽为风 (Xun) mutual hexagram."""
    result = calculate_hu_gua(57, [1, 0, 0, 0, 0, 1])
    # Lower (二三四): [0,0,0] = 坤 (trigram 0)
    # Upper (三四五): [0,0,0] = 坤 (trigram 0)
    # ID: (7-0)*8 + (7-0) + 1 = 64
    assert result == 64


def test_li_hu_gua():
    """Test: 离为火 (Li) mutual hexagram."""
    result = calculate_hu_gua(30, [1, 0, 1, 1, 0, 1])
    # Lower (二三四): [0,1,1] = 兑 (trigram 3)
    # Upper (三四五): [1,0,1] = 离 (trigram 5)
    # ID: (7-3)*8 + (7-5) + 1 = 4*8 + 2 + 1 = 13
    assert result == 13


def test_hexagram_3_hu_gua():
    """Test: 水雷屯 (hexagram 3) mutual hexagram."""
    result = calculate_hu_gua(3, [0, 1, 0, 1, 0, 0])
    assert result == 22


def test_algorithm_invariant():
    """Verify trigram calculation."""
    from core.hu_gua import calculate_trigram_value

    assert calculate_trigram_value([1, 1, 1]) == 7
    assert calculate_trigram_value([0, 0, 0]) == 0
    assert calculate_trigram_value([1, 0, 0]) == 1


def test_hu_gua_self_inverse():
    """Test that 乾 and 坤 are self-inverse."""
    assert calculate_hu_gua(1, [1, 1, 1, 1, 1, 1]) == 1
    assert calculate_hu_gua(64, [0, 0, 0, 0, 0, 0]) == 64
