"""Tests for core/models.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import (
    YaoPosition,
    QuestionContext,
    HexagramContext,
    YaoAnalysis,
    HuGuaContext,
    DecisionReport,
)


class TestYaoPosition:
    """Tests for YaoPosition enum"""

    def test_enum_values(self):
        """验证6个爻位枚举值"""
        assert len(YaoPosition) == 6
        assert YaoPosition.INITIAL.value == 1
        assert YaoPosition.SECOND.value == 2
        assert YaoPosition.THIRD.value == 3
        assert YaoPosition.FOURTH.value == 4
        assert YaoPosition.FIFTH.value == 5
        assert YaoPosition.TOP.value == 6

    def test_role_property(self):
        """验证role属性返回正确的分析角色"""
        assert YaoPosition.INITIAL.role == "环境感知"
        assert YaoPosition.SECOND.role == "资源配置"
        assert YaoPosition.THIRD.role == "风险评估"
        assert YaoPosition.FOURTH.role == "策略执行"
        assert YaoPosition.FIFTH.role == "长期规划"
        assert YaoPosition.TOP.role == "结果复盘"

    def test_name_cn_property(self):
        """验证name_cn属性返回正确的中文名称"""
        assert YaoPosition.INITIAL.name_cn == "初爻"
        assert YaoPosition.SECOND.name_cn == "二爻"
        assert YaoPosition.THIRD.name_cn == "三爻"
        assert YaoPosition.FOURTH.name_cn == "四爻"
        assert YaoPosition.FIFTH.name_cn == "五爻"
        assert YaoPosition.TOP.name_cn == "上爻"


class TestHuGuaContext:
    """Tests for HuGuaContext dataclass"""

    def test_creation(self):
        """验证HuGuaContext可以正常创建"""
        ctx = HuGuaContext(
            original_hexagram_id=1,
            hu_gua_id=5,
            lower_trigram=3,
            upper_trigram=7,
        )
        assert ctx.original_hexagram_id == 1
        assert ctx.hu_gua_id == 5
        assert ctx.lower_trigram == 3
        assert ctx.upper_trigram == 7


class TestHexagramContext:
    """Tests for HexagramContext dataclass"""

    def test_creation_with_hu_gua_id(self):
        """验证HexagramContext支持hu_gua_id字段"""
        question = QuestionContext(
            raw_question="test",
            question_type="创业决策",
            background="test background",
            constraints="test constraints",
            expected_outcome="test outcome",
            time_horizon="3个月",
            risk_tolerance="中",
            is_complete=True,
        )
        ctx = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="test reason",
            hexagram_data={},
            hu_gua_id=5,
        )
        assert ctx.hu_gua_id == 5

    def test_backward_compatibility(self):
        """验证向后兼容：hu_gua_id为可选字段"""
        question = QuestionContext(
            raw_question="test",
            question_type="创业决策",
            background="test background",
            constraints="test constraints",
            expected_outcome="test outcome",
            time_horizon="3个月",
            risk_tolerance="中",
            is_complete=True,
        )
        ctx = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="test reason",
            hexagram_data={},
        )
        assert ctx.hu_gua_id is None


class TestQuestionContext:
    """Tests for QuestionContext dataclass"""

    def test_creation(self):
        """验证QuestionContext可以正常创建"""
        ctx = QuestionContext(
            raw_question="我想辞职创业",
            question_type="创业决策",
            background="副业收入1万",
            constraints="资金有限",
            expected_outcome="顺利创业",
            time_horizon="3个月",
            risk_tolerance="中",
        )
        assert ctx.raw_question == "我想辞职创业"
        assert ctx.is_complete is False


class TestYaoAnalysis:
    """Tests for YaoAnalysis dataclass"""

    def test_creation(self):
        """验证YaoAnalysis可以正常创建"""
        analysis = YaoAnalysis(
            position=1,
            line_name="初九",
            yao_ci="潜龙勿用",
            analysis="当前宜静不宜动",
            advice="继续积累",
            risks="冒进风险",
        )
        assert analysis.position == 1
        assert analysis.line_name == "初九"


class TestDecisionReport:
    """Tests for DecisionReport dataclass"""

    def test_creation(self):
        """验证DecisionReport可以正常创建"""
        question = QuestionContext(
            raw_question="test",
            question_type="创业决策",
            background="test",
            constraints="test",
            expected_outcome="test",
            time_horizon="3个月",
            risk_tolerance="中",
            is_complete=True,
        )
        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="test",
            hexagram_data={},
        )
        yao_analyses = [
            YaoAnalysis(
                position=1,
                line_name="初九",
                yao_ci="潜龙勿用",
                analysis="test",
                advice="test",
                risks="test",
            )
        ]
        report = DecisionReport(
            question=question,
            hexagram=hexagram,
            yao_analyses=yao_analyses,
            overall_advice="综合建议",
            key_risks="风险提示",
            timing_judgment="时机判断",
            next_steps=["步骤1", "步骤2"],
        )
        assert len(report.yao_analyses) == 1
        assert len(report.next_steps) == 2
