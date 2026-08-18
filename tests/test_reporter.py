"""Tests for ReporterAgent with hu_gua integration."""

import pytest
from core.hu_gua import calculate_hu_gua, calculate_trigram_value
from core.models import (
    DecisionReport,
    HexagramContext,
    QuestionContext,
    YaoAnalysis,
)
from agents.reporter import (
    ReporterAgent,
    ReporterConfig,
    get_trigram_name,
    get_trigram_meaning,
)


def test_trigram_names():
    """Test trigram name mapping."""
    assert get_trigram_name(0) == "坤"
    assert get_trigram_name(7) == "乾"
    assert get_trigram_name(4) == "巽"


def test_trigram_meanings():
    """Test trigram meaning mapping."""
    assert "柔顺" in get_trigram_meaning(0)
    assert "刚健" in get_trigram_meaning(7)


def test_reporter_config_defaults():
    """Test ReporterConfig default values."""
    config = ReporterConfig()
    assert config.llm_call is None
    assert config.include_hu_gua is True


def test_reporter_config_custom():
    """Test ReporterConfig with custom values."""
    mock_llm = lambda s, p: "response"
    config = ReporterConfig(llm_call=mock_llm, include_hu_gua=False)
    assert config.llm_call is mock_llm
    assert config.include_hu_gua is False


def test_reporter_without_hu_gua():
    """Test ReporterAgent without hu_gua analysis."""
    config = ReporterConfig(include_hu_gua=False)
    agent = ReporterAgent(config)

    question = QuestionContext(
        raw_question="测试问题",
        question_type="职业选择",
        background="测试背景",
        constraints="测试约束",
        expected_outcome="测试期望",
        time_horizon="短期",
        risk_tolerance="中",
    )

    hexagram = HexagramContext(
        question=question,
        hexagram_id=1,
        hexagram_name="乾为天",
        match_reason="测试匹配",
        hexagram_data={"lines": [{"line_name": "初九", "yao_ci": "潜龙勿用"}]},
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

    report = agent.generate_report(question, hexagram, yao_analyses)

    assert isinstance(report, DecisionReport)
    assert report.hu_gua_analysis is None


def test_reporter_with_hu_gua():
    """Test ReporterAgent with hu_gua analysis."""
    config = ReporterConfig(include_hu_gua=True)
    agent = ReporterAgent(config)

    question = QuestionContext(
        raw_question="测试问题",
        question_type="创业决策",
        background="测试背景",
        constraints="测试约束",
        expected_outcome="测试期望",
        time_horizon="中期",
        risk_tolerance="高",
    )

    hexagram_data = {
        "lines": [
            {"line_name": "初九", "yao_ci": "潜龙勿用"},
            {"line_name": "九二", "yao_ci": "见龙在田"},
            {"line_name": "九三", "yao_ci": "君子终日乾乾"},
            {"line_name": "九四", "yao_ci": "或跃在渊"},
            {"line_name": "九五", "yao_ci": "飞龙在天"},
            {"line_name": "上九", "yao_ci": "亢龙有悔"},
        ]
    }

    hexagram = HexagramContext(
        question=question,
        hexagram_id=1,
        hexagram_name="乾为天",
        match_reason="测试匹配",
        hexagram_data=hexagram_data,
    )

    yao_analyses = [
        YaoAnalysis(
            position=i,
            line_name=f"第{i}爻",
            yao_ci=f"爻辞{i}",
            analysis="分析",
            advice="建议",
            risks="风险",
        )
        for i in range(1, 7)
    ]

    report = agent.generate_report(question, hexagram, yao_analyses)

    assert isinstance(report, DecisionReport)
    assert report.hu_gua_analysis is not None
    assert "互卦" in report.hu_gua_analysis
    assert "乾为天" in report.hu_gua_analysis


def test_hu_gua_calculation_integration():
    """Test that hu_gua is calculated correctly in ReporterAgent."""
    lines = [1, 1, 1, 1, 1, 1]
    hu_gua_id = calculate_hu_gua(1, lines)
    assert hu_gua_id == 1


def test_reporter_uses_binary_code_for_hu_gua():
    """Transformed line dictionaries must not collapse every mutual gua to 64."""
    question = QuestionContext(
        raw_question="测试",
        question_type="创业",
        background="",
        constraints="",
        expected_outcome="",
        time_horizon="中期",
        risk_tolerance="中",
    )
    hexagram = HexagramContext(
        question=question,
        hexagram_id=3,
        hexagram_name="屯",
        match_reason="测试",
        hexagram_data={
            "binary_code": [1, 0, 0, 0, 1, 0],
            "lines": [
                {"line_name": name, "yao_ci": "测试爻辞"}
                for name in ["初九", "六二", "六三", "六四", "九五", "上六"]
            ],
        },
    )
    section = ReporterAgent(ReporterConfig())._generate_hu_gua_analysis(hexagram)
    assert "互卦：第60卦" in section


def test_local_startup_report_has_decision_contract():
    question = QuestionContext(
        raw_question="有原型和两个试用客户，现金流只够四个月，是否全职投入？",
        question_type="创业",
        background="",
        constraints="现金流只够四个月",
        expected_outcome="判断是否全职",
        time_horizon="14天",
        risk_tolerance="中",
    )
    hexagram = HexagramContext(
        question=question,
        hexagram_id=3,
        hexagram_name="屯",
        match_reason="现金跑道验证",
        hexagram_data={
            "binary_code": [1, 0, 0, 0, 1, 0],
            "lines": [
                {"line_name": name, "yao_ci": "测试"}
                for name in ["初九", "六二", "六三", "六四", "九五", "上六"]
            ],
        },
    )
    analyses = [
        YaoAnalysis(i, f"第{i}爻", "测试", "分析", "建议", "风险")
        for i in range(1, 7)
    ]
    report = ReporterAgent(ReporterConfig()).generate_report(
        question, hexagram, analyses
    )
    assert report.decision_tendency == "有条件推进"
    assert len(report.decision_conditions) >= 3
    assert len(report.stop_conditions) >= 3
    assert "14 天" in report.review_trigger
    assert any("付费" in item for item in report.missing_information)


def test_local_health_report_defers_to_professional_care():
    question = QuestionContext(
        raw_question="身体不舒服是否继续高强度工作？",
        question_type="健康",
        background="",
        constraints="",
        expected_outcome="",
        time_horizon="当前",
        risk_tolerance="中",
    )
    hexagram = HexagramContext(
        question=question,
        hexagram_id=52,
        hexagram_name="艮",
        match_reason="健康停止",
        hexagram_data={
            "binary_code": [0, 0, 1, 0, 0, 1],
            "lines": [{"line_name": "初六", "yao_ci": "测试"}] * 6,
        },
    )
    analyses = [YaoAnalysis(i, f"第{i}爻", "测试", "分析", "建议", "风险") for i in range(1, 7)]
    report = ReporterAgent(ReporterConfig()).generate_report(question, hexagram, analyses)
    assert "就医" in report.overall_advice
    assert any("危险信号" in item for item in report.missing_information)
    assert "专业医疗评估" in report.review_trigger


def test_hu_gua_trigram_extraction():
    """Test trigram extraction from yao lines."""
    lower = [1, 1, 1]
    upper = [1, 1, 1]
    assert calculate_trigram_value(lower) == 7
    assert calculate_trigram_value(upper) == 7


def test_format_report_text():
    """Test report text formatting."""
    config = ReporterConfig()
    agent = ReporterAgent(config)

    question = QuestionContext(
        raw_question="测试",
        question_type="测试",
        background="测试",
        constraints="测试",
        expected_outcome="测试",
        time_horizon="测试",
        risk_tolerance="中",
    )

    hexagram = HexagramContext(
        question=question,
        hexagram_id=1,
        hexagram_name="乾为天",
        match_reason="测试",
        hexagram_data={"lines": []},
    )

    yao_analyses = [
        YaoAnalysis(
            position=1,
            line_name="初九",
            yao_ci="潜龙勿用",
            analysis="分析",
            advice="建议",
            risks="风险",
        )
    ]

    report = agent.generate_report(question, hexagram, yao_analyses)
    text = agent.format_report_text(report)

    assert "决策参考报告" in text
    assert "乾为天" in text
    assert "六爻分析" in text
    assert "综合建议" in text


def test_reporter_preserves_yao_analyses():
    """Test that ReporterAgent preserves all yao analyses."""
    config = ReporterConfig(include_hu_gua=True)
    agent = ReporterAgent(config)

    question = QuestionContext(
        raw_question="问题",
        question_type="其他",
        background="背景",
        constraints="约束",
        expected_outcome="期望",
        time_horizon="短期",
        risk_tolerance="低",
    )

    hexagram = HexagramContext(
        question=question,
        hexagram_id=3,
        hexagram_name="水雷屯",
        match_reason="匹配",
        hexagram_data={"lines": [{"line_name": "初九", "yao_ci": "磐桓"}] * 6},
    )

    yao_analyses = [
        YaoAnalysis(
            position=i,
            line_name=f"九{i}",
            yao_ci=f"辞{i}",
            analysis=f"分析{i}",
            advice=f"建议{i}",
            risks=f"风险{i}",
        )
        for i in range(1, 7)
    ]

    report = agent.generate_report(question, hexagram, yao_analyses)

    assert len(report.yao_analyses) == 6
    for i, ya in enumerate(report.yao_analyses, 1):
        assert ya.position == i


class TestReporterEdgeCases:
    """Edge case tests for ReporterAgent."""

    def test_generate_report_with_llm_empty_response(self):
        """Test generate_report when LLM returns empty string."""

        def empty_llm(system: str, user: str) -> str:
            return ""

        config = ReporterConfig(llm_call=empty_llm)
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="测试问题",
            question_type="创业",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="中期",
            risk_tolerance="高",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾为天",
            match_reason="测试",
            hexagram_data={
                "lines": [
                    {"line_name": "初九", "yao_ci": "潜龙勿用"},
                    {"line_name": "九二", "yao_ci": "见龙在田"},
                    {"line_name": "九三", "yao_ci": "君子终日乾乾"},
                    {"line_name": "九四", "yao_ci": "或跃在渊"},
                    {"line_name": "九五", "yao_ci": "飞龙在天"},
                    {"line_name": "上九", "yao_ci": "亢龙有悔"},
                ]
            },
        )

        yao_analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci=f"辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}",
                risks=f"风险{i}",
            )
            for i in range(1, 7)
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert report.overall_advice is not None
        assert report.next_steps is not None

    def test_generate_report_with_llm_malformed_response(self):
        """Test generate_report when LLM returns malformed response."""

        def malformed_llm(system: str, user: str) -> str:
            return "这是一段没有正确格式的响应"

        config = ReporterConfig(llm_call=malformed_llm)
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="测试",
            question_type="其他",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="短期",
            risk_tolerance="中",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="测试",
            hexagram_data={"lines": [{"line_name": "初九", "yao_ci": "潜龙"}] * 6},
        )

        yao_analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci=f"辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}",
                risks=f"风险{i}",
            )
            for i in range(1, 7)
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert report.overall_advice is not None

    def test_generate_report_with_llm_missing_sections(self):
        """Test generate_report when LLM response is missing some sections."""

        def partial_llm(system: str, user: str) -> str:
            return "综合建议：这是建议\n关键风险：这是风险"

        config = ReporterConfig(llm_call=partial_llm)
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="测试",
            question_type="其他",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="短期",
            risk_tolerance="中",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="测试",
            hexagram_data={"lines": [{"line_name": "初九", "yao_ci": "潜龙"}] * 6},
        )

        yao_analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci=f"辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}",
                risks=f"风险{i}",
            )
            for i in range(1, 7)
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert report.overall_advice is not None
        assert report.timing_judgment is not None
        assert len(report.next_steps) > 0

    def test_generate_report_with_partial_yao_analyses(self):
        """Test generate_report with fewer than 6 yao analyses."""
        config = ReporterConfig()
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="测试",
            question_type="其他",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="短期",
            risk_tolerance="中",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="测试",
            hexagram_data={"lines": [{"line_name": "初九", "yao_ci": "潜龙"}] * 6},
        )

        yao_analyses = [
            YaoAnalysis(
                position=1,
                line_name="初九",
                yao_ci="潜龙",
                analysis="分析",
                advice="建议",
                risks="风险",
            )
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert len(report.yao_analyses) == 1
        assert report.next_steps is not None

    def test_format_report_with_empty_next_steps(self):
        """Test format_report_text when next_steps is empty list."""
        config = ReporterConfig()
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="测试",
            question_type="其他",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="短期",
            risk_tolerance="中",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="测试",
            hexagram_data={"lines": [{"line_name": "初九", "yao_ci": "潜龙"}] * 6},
        )

        yao_analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci=f"辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}",
                risks=f"风险{i}",
            )
            for i in range(1, 7)
        ]

        from core.models import DecisionReport

        report = DecisionReport(
            question=question,
            hexagram=hexagram,
            yao_analyses=yao_analyses,
            overall_advice="建议",
            key_risks="风险",
            timing_judgment="时机",
            next_steps=[],
            hu_gua_analysis=None,
        )

        text = agent.format_report_text(report)

        assert "决策参考报告" in text

    def test_hu_gua_with_no_lines(self):
        """Test hu_gua generation when hexagram has no lines."""
        config = ReporterConfig(include_hu_gua=True)
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="测试",
            question_type="其他",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="短期",
            risk_tolerance="中",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="测试",
            hexagram_data={"lines": []},
        )

        yao_analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci=f"辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}",
                risks=f"风险{i}",
            )
            for i in range(1, 7)
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert report.hu_gua_analysis is not None
        assert "完整的六爻数据" in report.hu_gua_analysis

    def test_llm_failure_fallback_generates_real_content(self):
        def failing_llm(system: str, user: str) -> str:
            raise Exception("LLM unavailable")

        config = ReporterConfig(llm_call=failing_llm)
        agent = ReporterAgent(config)

        question = QuestionContext(
            raw_question="我应该创业吗？",
            question_type="创业",
            background="有资金支持",
            constraints="时间有限",
            expected_outcome="成功启动",
            time_horizon="中期",
            risk_tolerance="高",
        )

        hexagram = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾为天",
            match_reason="创业相关",
            hexagram_data={
                "lines": [
                    {"line_name": "初九", "yao_ci": "潜龙勿用"},
                    {"line_name": "九二", "yao_ci": "见龙在田"},
                    {"line_name": "九三", "yao_ci": "君子终日乾乾"},
                    {"line_name": "九四", "yao_ci": "或跃在渊"},
                    {"line_name": "九五", "yao_ci": "飞龙在天"},
                    {"line_name": "上九", "yao_ci": "亢龙有悔"},
                ]
            },
        )

        yao_analyses = [
            YaoAnalysis(
                position=1,
                line_name="初九",
                yao_ci="潜龙勿用",
                analysis="时机未到",
                advice="先积累经验和资源",
                risks="盲目行动可能导致失败",
            ),
            YaoAnalysis(
                position=2,
                line_name="九二",
                yao_ci="见龙在田",
                analysis="初露锋芒",
                advice="寻找合适的切入点",
                risks="过早暴露可能引来竞争",
            ),
            YaoAnalysis(
                position=3,
                line_name="九三",
                yao_ci="君子终日乾乾",
                analysis="勤奋努力",
                advice="持续提升能力",
                risks="过度劳累影响健康",
            ),
            YaoAnalysis(
                position=4,
                line_name="九四",
                yao_ci="或跃在渊",
                analysis="审时度势",
                advice="等待最佳时机",
                risks="犹豫不决错失良机",
            ),
            YaoAnalysis(
                position=5,
                line_name="九五",
                yao_ci="飞龙在天",
                analysis="大展宏图",
                advice="把握时机行动",
                risks="成功后的骄傲自满",
            ),
            YaoAnalysis(
                position=6,
                line_name="上九",
                yao_ci="亢龙有悔",
                analysis="物极必反",
                advice="保持谦逊谨慎",
                risks="过度扩张导致衰退",
            ),
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert report.overall_advice is not None
        assert "待补充" not in report.overall_advice
        assert "待定" not in report.overall_advice
        assert "。。" not in report.overall_advice
        assert len(report.overall_advice) > 20

        assert report.key_risks is not None
        assert "待评估" not in report.key_risks
        assert "需要关注" not in report.key_risks or len(report.key_risks) > 10

        assert report.timing_judgment is not None
        assert "时机判断" != report.timing_judgment
        assert len(report.timing_judgment) > 5

        assert report.next_steps is not None
        assert len(report.next_steps) > 0
        assert "待生成" not in str(report.next_steps)
        assert "步骤 1" not in str(report.next_steps)

        assert "乾为天" in report.overall_advice or "第 1 卦" in report.overall_advice

    def test_local_fallback_normalizes_advice_punctuation(self):
        agent = ReporterAgent(ReporterConfig(include_hu_gua=False))
        question = QuestionContext(
            raw_question="测试问题",
            question_type="创业",
            background="背景",
            constraints="约束",
            expected_outcome="期望",
            time_horizon="中期",
            risk_tolerance="中",
        )
        hexagram = HexagramContext(
            question=question,
            hexagram_id=3,
            hexagram_name="屯",
            match_reason="测试",
            hexagram_data={"lines": []},
        )
        yao_analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"第{i}爻",
                yao_ci=f"爻辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}。",
                risks=f"风险{i}。",
            )
            for i in range(1, 7)
        ]

        report = agent.generate_report(question, hexagram, yao_analyses)

        assert "。。" not in report.overall_advice
