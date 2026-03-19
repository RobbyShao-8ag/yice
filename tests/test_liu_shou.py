"""Tests for 六兽 (Liu Shou / Six Beasts) allocation based on day stem (日干).

This test module covers the six beasts allocation rules in divination.
六兽 include: 青龙, 朱雀, 勾陈, 螣蛇, 白虎, 玄武

Reference: 梅花易数六兽配日干
"""

import pytest


class TestLiuShouAllocation:
    """Test suite for 六兽 allocation based on day stem (日干)."""

    def test_jia_day_stem(self):
        """甲日：六兽顺序为青龙、朱雀、勾陈、螣蛇、白虎、玄武.
        
        Day stem 甲 (Jia) starts with 青龙 at 初爻.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('甲')
        expected = ['青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武']
        assert result == expected

    def test_yi_day_stem(self):
        """乙日：六兽顺序为青龙、朱雀、勾陈、螣蛇、白虎、玄武.
        
        Day stem 乙 (Yi) starts with 青龙 at 初爻, same as 甲.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('乙')
        expected = ['青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武']
        assert result == expected

    def test_bing_day_stem(self):
        """丙日：六兽顺序为朱雀、勾陈、螣蛇、白虎、玄武、青龙.
        
        Day stem 丙 (Bing) starts with 朱雀 at 初爻.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('丙')
        expected = ['朱雀', '勾陈', '螣蛇', '白虎', '玄武', '青龙']
        assert result == expected

    def test_ding_day_stem(self):
        """丁日：六兽顺序为朱雀、勾陈、螣蛇、白虎、玄武、青龙.
        
        Day stem 丁 (Ding) starts with 朱雀 at 初爻, same as 丙.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('丁')
        expected = ['朱雀', '勾陈', '螣蛇', '白虎', '玄武', '青龙']
        assert result == expected

    def test_wu_day_stem(self):
        """戊日：六兽顺序为勾陈、螣蛇、白虎、玄武、青龙、朱雀.
        
        Day stem 戊 (Wu) starts with 勾陈 at 初爻.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('戊')
        expected = ['勾陈', '螣蛇', '白虎', '玄武', '青龙', '朱雀']
        assert result == expected

    def test_ji_day_stem(self):
        """己日：六兽顺序为勾陈、螣蛇、白虎、玄武、青龙、朱雀.
        
        Day stem 己 (Ji) starts with 勾陈 at 初爻, same as 戊.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('己')
        expected = ['勾陈', '螣蛇', '白虎', '玄武', '青龙', '朱雀']
        assert result == expected

    def test_geng_day_stem(self):
        """庚日：六兽顺序为白虎、玄武、青龙、朱雀、勾陈、螣蛇.
        
        Day stem 庚 (Geng) starts with 白虎 at 初爻.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('庚')
        expected = ['白虎', '玄武', '青龙', '朱雀', '勾陈', '螣蛇']
        assert result == expected

    def test_xin_day_stem(self):
        """辛日：六兽顺序为白虎、玄武、青龙、朱雀、勾陈、螣蛇.
        
        Day stem 辛 (Xin) starts with 白虎 at 初爻, same as 庚.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('辛')
        expected = ['白虎', '玄武', '青龙', '朱雀', '勾陈', '螣蛇']
        assert result == expected

    def test_ren_day_stem(self):
        """壬日：六兽顺序为玄武、青龙、朱雀、勾陈、螣蛇、白虎.
        
        Day stem 壬 (Ren) starts with 玄武 at 初爻.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('壬')
        expected = ['玄武', '青龙', '朱雀', '勾陈', '螣蛇', '白虎']
        assert result == expected

    def test_gui_day_stem(self):
        """癸日：六兽顺序为玄武、青龙、朱雀、勾陈、螣蛇、白虎.
        
        Day stem 癸 (Gui) starts with 玄武 at 初爻, same as 壬.
        """
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts('癸')
        expected = ['玄武', '青龙', '朱雀', '勾陈', '螣蛇', '白虎']
        assert result == expected


class TestLiuShouMeanings:
    """Test suite for 六兽 meanings and attributes."""

    def test_qing_long_meaning(self):
        """青龙：吉神，木行，象征喜庆、财富、婚姻."""
        from core.liu_shou import get_liu_shou_meaning
        
        result = get_liu_shou_meaning('青龙')
        assert result['属性'] == '吉神'
        assert result['五行'] == '木'
        assert '喜庆' in result['象征']
        assert '财富' in result['象征']
        assert '婚姻' in result['象征']

    def test_que_que_meaning(self):
        """朱雀：凶神，火行，象征文书、口舌、信息."""
        from core.liu_shou import get_liu_shou_meaning
        
        result = get_liu_shou_meaning('朱雀')
        assert result['属性'] == '凶神'
        assert result['五行'] == '火'
        assert '文书' in result['象征']
        assert '口舌' in result['象征']
        assert '信息' in result['象征']

    def test_gou_chen_meaning(self):
        """勾陈：凶神，土行，象征田土、牢狱、迟滞."""
        from core.liu_shou import get_liu_shou_meaning
        
        result = get_liu_shou_meaning('勾陈')
        assert result['属性'] == '凶神'
        assert result['五行'] == '土'
        assert '田土' in result['象征']
        assert '牢狱' in result['象征']
        assert '迟滞' in result['象征']

    def test_teng_she_meaning(self):
        """螣蛇：凶神，土行，象征惊恐、怪异、虚惊."""
        from core.liu_shou import get_liu_shou_meaning
        
        result = get_liu_shou_meaning('螣蛇')
        assert result['属性'] == '凶神'
        assert result['五行'] == '土'
        assert '惊恐' in result['象征']
        assert '怪异' in result['象征']
        assert '虚惊' in result['象征']

    def test_bai_hu_meaning(self):
        """白虎：凶神，金行，象征血光、丧事、凶险."""
        from core.liu_shou import get_liu_shou_meaning
        
        result = get_liu_shou_meaning('白虎')
        assert result['属性'] == '凶神'
        assert result['五行'] == '金'
        assert '血光' in result['象征']
        assert '丧事' in result['象征']
        assert '凶险' in result['象征']

    def test_xuan_wu_meaning(self):
        """玄武：凶神，水行，象征盗贼、暗昧、欺诈."""
        from core.liu_shou import get_liu_shou_meaning
        
        result = get_liu_shou_meaning('玄武')
        assert result['属性'] == '凶神'
        assert result['五行'] == '水'
        assert '盗贼' in result['象征']
        assert '暗昧' in result['象征']
        assert '欺诈' in result['象征']

    def test_all_beasts_have_meanings(self):
        """Verify all 6 beasts have meanings defined."""
        from core.liu_shou import allocate_six_beasts, get_liu_shou_meaning
        
        beasts = allocate_six_beasts('甲')  # Any valid stem
        for beast in beasts:
            meaning = get_liu_shou_meaning(beast)
            assert '属性' in meaning
            assert '象征' in meaning
            assert '五行' in meaning


class TestLiuShouEdgeCases:
    """Edge case tests for 六兽 functions."""

    def test_invalid_day_stem_raises(self):
        """Invalid day stem should raise ValueError."""
        from core.liu_shou import allocate_six_beasts
        
        with pytest.raises(ValueError):
            allocate_six_beasts('X')  # Not a valid stem

    def test_invalid_day_stem_number_raises(self):
        """Invalid day stem (number) should raise ValueError."""
        from core.liu_shou import allocate_six_beasts
        
        with pytest.raises(ValueError):
            allocate_six_beasts('1')

    def test_empty_day_stem_raises(self):
        """Empty day stem should raise ValueError."""
        from core.liu_shou import allocate_six_beasts
        
        with pytest.raises(ValueError):
            allocate_six_beasts('')

    def test_invalid_beast_raises(self):
        """Invalid beast name should raise KeyError or ValueError."""
        from core.liu_shou import get_liu_shou_meaning
        
        with pytest.raises((KeyError, ValueError)):
            get_liu_shou_meaning('InvalidBeast')

    def test_all_stems_return_six_beasts(self):
        """All valid stems should return exactly 6 beasts."""
        from core.liu_shou import allocate_six_beasts
        
        valid_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        for stem in valid_stems:
            result = allocate_six_beasts(stem)
            assert len(result) == 6

    def test_beasts_are_unique(self):
        """Each beast should appear exactly once in allocation."""
        from core.liu_shou import allocate_six_beasts
        
        valid_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        expected_beasts = {'青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武'}
        
        for stem in valid_stems:
            result = allocate_six_beasts(stem)
            assert set(result) == expected_beasts


class TestLiuShouParametrized:
    """Parametrized tests for 六兽 allocation."""

    @pytest.mark.parametrize("stem,expected_first", [
        ('甲', '青龙'),
        ('乙', '青龙'),
        ('丙', '朱雀'),
        ('丁', '朱雀'),
        ('戊', '勾陈'),
        ('己', '勾陈'),
        ('庚', '白虎'),
        ('辛', '白虎'),
        ('壬', '玄武'),
        ('癸', '玄武'),
    ])
    def test_first_beast_by_stem(self, stem, expected_first):
        """Verify the first beast (初爻) for each day stem."""
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts(stem)
        assert result[0] == expected_first

    @pytest.mark.parametrize("stem,expected_order", [
        ('甲', ['青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武']),
        ('乙', ['青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武']),
        ('丙', ['朱雀', '勾陈', '螣蛇', '白虎', '玄武', '青龙']),
        ('丁', ['朱雀', '勾陈', '螣蛇', '白虎', '玄武', '青龙']),
        ('戊', ['勾陈', '螣蛇', '白虎', '玄武', '青龙', '朱雀']),
        ('己', ['勾陈', '螣蛇', '白虎', '玄武', '青龙', '朱雀']),
        ('庚', ['白虎', '玄武', '青龙', '朱雀', '勾陈', '螣蛇']),
        ('辛', ['白虎', '玄武', '青龙', '朱雀', '勾陈', '螣蛇']),
        ('壬', ['玄武', '青龙', '朱雀', '勾陈', '螣蛇', '白虎']),
        ('癸', ['玄武', '青龙', '朱雀', '勾陈', '螣蛇', '白虎']),
    ])
    def test_complete_order_by_stem(self, stem, expected_order):
        """Verify complete 六兽 order for each day stem."""
        from core.liu_shou import allocate_six_beasts
        
        result = allocate_six_beasts(stem)
        assert result == expected_order
