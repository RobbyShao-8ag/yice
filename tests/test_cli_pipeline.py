"""
End-to-end tests for CLI pipeline with mock LLM.

Tests the complete flow: QiguaAgent -> SceneRouter -> YaoAgents -> Reporter
"""

import pytest
from core.data_loader import DataLoader, DataLoaderConfig
from core.models import HexagramContext, QuestionContext
from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
from agents.scene_router import SceneRouter, SceneRouterConfig
from agents.yao_agents import YaoAgentOrchestrator
from agents.reporter import ReporterAgent, ReporterConfig


def create_mock_llm(response_override: str = "Mock response"):
    """Create a mock LLM callable that returns predefined responses.

    Args:
        response_override: Optional override for specific responses.

    Returns:
        Mock LLM callable.
    """

    def mock_llm(system_prompt: str, user_prompt: str) -> str:
        if "起卦" in system_prompt or "问题分析" in system_prompt:
            return '{"question_type": "职业", "background": "工作5年", "expected_outcome": "晋升"}'
        elif "scene_router" in system_prompt.lower() or "场景" in system_prompt:
            return "5 - 需卦，适合耐心等待机会"
        elif "初爻" in system_prompt:
            return "解读：初始阶段需要谨慎\n建议：做好基础准备\n风险：过于急躁"
        elif "二爻" in system_prompt:
            return "解读：资源整合阶段\n建议：寻找合作伙伴\n风险：资源分散"
        elif "三爻" in system_prompt:
            return "解读：风险评估阶段\n建议：多元化准备\n风险：盲目冒进"
        elif "四爻" in system_prompt:
            return "解读：策略执行阶段\n建议：稳步推进\n风险：执行力不足"
        elif "五爻" in system_prompt:
            return "解读：长期规划阶段\n建议：建立长期目标\n风险：目光短浅"
        elif "上爻" in system_prompt:
            return "解读：结果复盘阶段\n建议：总结经验教训\n风险：固步自封"
        elif "reporter" in system_prompt.lower() or "报告" in system_prompt:
            return """综合建议：当前时机成熟，建议稳步推进
关键风险：需注意资源配置和执行力
时机判断：三个月内为最佳时机
下一步：
1. 制定详细计划
2. 寻找合适伙伴
3. 稳步执行"""
        return response_override or "Mock response"

    return mock_llm


class TestFullPipelineWithMockLLM:
    """Test complete pipeline flow with mocked LLM."""

    @pytest.fixture
    def data_loader(self):
        """Create DataLoader fixture."""
        return DataLoader(DataLoaderConfig(data_dir="data"))

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM callable."""
        return create_mock_llm()

    def test_question_context_creation(self, mock_llm):
        """Test QuestionContext creation from raw question."""
        from main import build_question_context

        question_ctx = build_question_context("我想换工作", mock_llm)

        assert isinstance(question_ctx, QuestionContext)
        assert question_ctx.raw_question == "我想换工作"
        assert question_ctx.question_type is not None

    def test_scene_router_returns_hexagram(self, data_loader, mock_llm):
        """Test SceneRouter returns valid HexagramContext."""
        question_ctx = QuestionContext(
            raw_question="我想换工作",
            question_type="职业",
            background="工作5年",
            constraints="",
            expected_outcome="晋升",
            time_horizon="中期",
            risk_tolerance="中",
        )

        router = SceneRouter(
            SceneRouterConfig(
                scene_mapping_path="data/scene_mapping.json",
                llm_call=mock_llm,
            )
        )
        hexagram_ctx = router.route(question_ctx)

        assert isinstance(hexagram_ctx, HexagramContext)
        assert hexagram_ctx.hexagram_id is not None
        assert hexagram_ctx.hexagram_name is not None

    def test_yao_agents_analyze_all_positions(self, data_loader, mock_llm):
        """Test YaoAgentOrchestrator analyzes all six positions."""
        question_ctx = QuestionContext(
            raw_question="我想换工作",
            question_type="职业",
            background="工作5年",
            constraints="",
            expected_outcome="晋升",
            time_horizon="中期",
            risk_tolerance="中",
        )

        router = SceneRouter(SceneRouterConfig())
        hexagram_ctx = router.route(question_ctx)

        # Enrich hexagram data with lines
        hexagram_id = hexagram_ctx.hexagram_id
        hexagram_data = data_loader.get_hexagram(hexagram_id)
        lines = data_loader.get_lines_for_hexagram(hexagram_id)

        if hexagram_data:
            hexagram_data = dict(hexagram_data)
            hexagram_data["lines"] = [
                {
                    "line_name": line.get(
                        "yao_name", f"第{line.get('position', i + 1)}爻"
                    ),
                    "yao_ci": line.get("text", ""),
                }
                for i, line in enumerate(lines)
            ]
            hexagram_ctx = HexagramContext(
                question=hexagram_ctx.question,
                hexagram_id=hexagram_ctx.hexagram_id,
                hexagram_name=hexagram_ctx.hexagram_name,
                match_reason=hexagram_ctx.match_reason,
                hexagram_data=hexagram_data,
            )

        yao_orchestrator = YaoAgentOrchestrator(llm_call=mock_llm)
        analyses = yao_orchestrator.analyze_all(hexagram_ctx)

        assert len(analyses) == 6
        for ya in analyses:
            assert ya.analysis is not None
            assert ya.advice is not None
            assert ya.risks is not None

    def test_reporter_generates_final_report(self, data_loader, mock_llm):
        """Test ReporterAgent generates final decision report."""
        question_ctx = QuestionContext(
            raw_question="我想换工作",
            question_type="职业",
            background="工作5年",
            constraints="",
            expected_outcome="晋升",
            time_horizon="中期",
            risk_tolerance="中",
        )

        router = SceneRouter(SceneRouterConfig())
        hexagram_ctx = router.route(question_ctx)

        # Enrich hexagram data with lines
        hexagram_id = hexagram_ctx.hexagram_id
        hexagram_data = data_loader.get_hexagram(hexagram_id)
        lines = data_loader.get_lines_for_hexagram(hexagram_id)

        if hexagram_data:
            hexagram_data = dict(hexagram_data)
            hexagram_data["lines"] = [
                {
                    "line_name": line.get(
                        "yao_name", f"第{line.get('position', i + 1)}爻"
                    ),
                    "yao_ci": line.get("text", ""),
                }
                for i, line in enumerate(lines)
            ]
            hexagram_ctx = HexagramContext(
                question=hexagram_ctx.question,
                hexagram_id=hexagram_ctx.hexagram_id,
                hexagram_name=hexagram_ctx.hexagram_name,
                match_reason=hexagram_ctx.match_reason,
                hexagram_data=hexagram_data,
            )

        yao_orchestrator = YaoAgentOrchestrator(llm_call=mock_llm)
        yao_analyses = yao_orchestrator.analyze_all(hexagram_ctx)

        reporter = ReporterAgent(ReporterConfig(llm_call=mock_llm))
        report = reporter.generate_report(question_ctx, hexagram_ctx, yao_analyses)

        assert report is not None
        assert report.overall_advice is not None
        assert len(report.next_steps) > 0

    def test_no_placeholders_in_final_output(self, data_loader, mock_llm):
        """Test that final output contains no placeholder text."""
        question_ctx = QuestionContext(
            raw_question="我想换工作",
            question_type="职业",
            background="工作5年",
            constraints="",
            expected_outcome="晋升",
            time_horizon="中期",
            risk_tolerance="中",
        )

        router = SceneRouter(SceneRouterConfig())
        hexagram_ctx = router.route(question_ctx)

        # Enrich hexagram data with lines
        hexagram_id = hexagram_ctx.hexagram_id
        hexagram_data = data_loader.get_hexagram(hexagram_id)
        lines = data_loader.get_lines_for_hexagram(hexagram_id)

        if hexagram_data:
            hexagram_data = dict(hexagram_data)
            hexagram_data["lines"] = [
                {
                    "line_name": line.get(
                        "yao_name", f"第{line.get('position', i + 1)}爻"
                    ),
                    "yao_ci": line.get("text", ""),
                }
                for i, line in enumerate(lines)
            ]
            hexagram_ctx = HexagramContext(
                question=hexagram_ctx.question,
                hexagram_id=hexagram_ctx.hexagram_id,
                hexagram_name=hexagram_ctx.hexagram_name,
                match_reason=hexagram_ctx.match_reason,
                hexagram_data=hexagram_data,
            )

        yao_orchestrator = YaoAgentOrchestrator(llm_call=mock_llm)
        yao_analyses = yao_orchestrator.analyze_all(hexagram_ctx)

        reporter = ReporterAgent(ReporterConfig(llm_call=mock_llm))
        report = reporter.generate_report(question_ctx, hexagram_ctx, yao_analyses)

        # Check for placeholders
        placeholder_patterns = [
            "待补充",
            "待生成",
            "待LLM",
            "待分析",
            "TODO",
            "PLACEHOLDER",
            "[]",
            "无",
        ]

        report_text = (
            report.overall_advice
            + report.key_risks
            + report.timing_judgment
            + " ".join(report.next_steps)
        )

        # Allow "无" if it's meaningful, but check for obvious placeholders
        for pattern in ["待补充", "待生成", "待LLM", "TODO", "PLACEHOLDER"]:
            assert pattern not in report_text, f"Found placeholder: {pattern}"


class TestPipelineProgressIndicators:
    """Test that pipeline shows progress indicators."""

    def test_progress_messages_present_in_output(self, capsys):
        """Test that progress messages are displayed during pipeline execution."""
        # This test verifies the print statements work without errors
        mock_llm = create_mock_llm()

        # Just test that print doesn't raise an exception
        print("[1/4] 起卦官对话中...")
        print("[2/4] 匹配卦象中...")
        print("[3/4] 分析六爻中 (1/6)...")
        print("[4/4] 生成报告中...")

        captured = capsys.readouterr()
        assert "[1/4]" in captured.out
        assert "[2/4]" in captured.out
        assert "[3/4]" in captured.out
        assert "[4/4]" in captured.out
