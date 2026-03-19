"""Tests for hexagram_relations module."""

import pytest
from core.hexagram_relations import (
    get_cuo_gua,
    get_zong_gua,
    get_jiao_gua,
    get_hu_gua,
)


class TestCuoGua:
    """Tests for get_cuo_gua function."""
    
    def test_cuo_gua_returns_int(self):
        """Cuo gua should return an integer."""
        result = get_cuo_gua(1)
        assert isinstance(result, int)


class TestZongGua:
    """Tests for get_zong_gua function."""
    
    def test_zong_gua_returns_int_or_none(self):
        """Zong gua should return int or None."""
        result = get_zong_gua(1)
        assert result is None or isinstance(result, int)
    
    def test_zong_gua_qian_is_none(self):
        """乾 is self-zong, returns None."""
        assert get_zong_gua(1) is None


class TestJiaoGua:
    """Tests for get_jiao_gua function."""
    
    def test_jiao_gua_returns_int(self):
        """Jiao gua should return an integer."""
        result = get_jiao_gua(1)
        assert isinstance(result, int)


class TestHuGua:
    """Tests for get_hu_gua function."""
    
    def test_hu_gua_returns_int(self):
        """Hu gua should return an integer."""
        result = get_hu_gua(1)
        assert isinstance(result, int)
    
    def test_hu_gua_qian(self):
        """互卦 of 乾 is itself."""
        assert get_hu_gua(1) == 1
