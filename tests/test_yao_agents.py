"""Tests for agents/yao_agents.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.yao_agents import (
    YaoAgent,
    YaoAgentConfig,
    YaoAgentOrchestrator,
    build_system_prompt,
    get_all_system_prompts,
)
from core.errors import PartialFailureError
from core.models import (
    HexagramContext,
    QuestionContext,
    YaoAnalysis,
    YaoPosition,
)


def make_question_context() -> QuestionContext:
    return QuestionContext(
        raw_question="我想辞职创业",
        question_type="创业决策",
        background="副业收入1万，主业稳定",
        constraints="资金有限，有房贷",
        expected_outcome="顺利创业",
        time_horizon="3个月",
        risk_tolerance="中",
        is_complete=True,
    )


def make_hexagram_context(
    question: QuestionContext | None = None,
    lines: list | None = None,
) -> HexagramContext:
    if question is None:
        question = make_question_context()
    if lines is None:
        lines = [
            {"line_name": "初九", "yao_ci": "潜龙勿用"},
            {"line_name": "九二", "yao_ci": "见龙在田，利见大人"},
            {"line_name": "九三", "yao_ci": "君子终日乾乾"},
            {"line_name": "九四", "yao_ci": "或跃在渊"},
            {"line_name": "九五", "yao_ci": "飞龙在天，利见大人"},
            {"line_name": "上九", "yao_ci": "亢龙有悔"},
        ]
    return HexagramContext(
        question=question,
        hexagram_id=1,
        hexagram_name="乾",
        match_reason="创业需刚健进取",
        hexagram_data={"lines": lines},
    )


class TestYaoPositionFusedRoles:
    """Tests for fused role definitions in YaoPosition enum"""

    def test_traditional_meaning_initial(self):
        assert YaoPosition.INITIAL.traditional_meaning == "根本"

    def test_traditional_meaning_second(self):
        assert YaoPosition.SECOND.traditional_meaning == "内中馈"

    def test_traditional_meaning_third(self):
        assert YaoPosition.THIRD.traditional_meaning == "君子终日乾乾"

    def test_traditional_meaning_fourth(self):
        assert YaoPosition.FOURTH.traditional_meaning == "门阙"

    def test_traditional_meaning_fifth(self):
        assert YaoPosition.FIFTH.traditional_meaning == "君位"

    def test_traditional_meaning_top(self):
        assert YaoPosition.TOP.traditional_meaning == "亢龙有悔"

    def test_fused_role_initial(self):
        assert YaoPosition.INITIAL.fused_role == "基础环境层"

    def test_fused_role_second(self):
        assert YaoPosition.SECOND.fused_role == "内部资源层"

    def test_fused_role_third(self):
        assert YaoPosition.THIRD.fused_role == "行动执行层"

    def test_fused_role_fourth(self):
        assert YaoPosition.FOURTH.fused_role == "关键转折层"

    def test_fused_role_fifth(self):
        assert YaoPosition.FIFTH.fused_role == "核心决策层"

    def test_fused_role_top(self):
        assert YaoPosition.TOP.fused_role == "终局反思层"

    def test_analysis_focus_initial(self):
        assert (
            "根本" in YaoPosition.INITIAL.analysis_focus
            or "环境" in YaoPosition.INITIAL.analysis_focus
        )

    def test_analysis_focus_contains_key_terms(self):
        focus_terms = {
            YaoPosition.INITIAL: "环境",
            YaoPosition.SECOND: "资源",
            YaoPosition.THIRD: "风险",
            YaoPosition.FOURTH: "策略",
            YaoPosition.FIFTH: "长远",
            YaoPosition.TOP: "反思",
        }
        for pos, term in focus_terms.items():
            assert term in pos.analysis_focus, (
                f"{pos.name_cn} analysis_focus should contain '{term}'"
            )


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function"""

    def test_contains_traditional_meaning(self):
        prompt = build_system_prompt(YaoPosition.INITIAL)
        assert "根本" in prompt

    def test_contains_modern_mapping(self):
        prompt = build_system_prompt(YaoPosition.INITIAL)
        assert "环境感知" in prompt

    def test_contains_fused_role(self):
        prompt = build_system_prompt(YaoPosition.INITIAL)
        assert "基础环境层" in prompt

    def test_contains_analysis_focus(self):
        prompt = build_system_prompt(YaoPosition.INITIAL)
        assert "环境基调" in prompt

    def test_all_positions_have_prompts(self):
        for pos in YaoPosition:
            prompt = build_system_prompt(pos)
            assert pos.traditional_meaning in prompt
            assert pos.role in prompt
            assert pos.fused_role in prompt

    def test_prompt_structure(self):
        prompt = build_system_prompt(YaoPosition.FIFTH)
        assert "传统含义" in prompt
        assert "现代映射" in prompt
        assert "融合角色" in prompt
        assert "君位" in prompt
        assert "长期规划" in prompt
        assert "核心决策层" in prompt


class TestGetAllSystemPrompts:
    """Tests for get_all_system_prompts function"""

    def test_returns_six_prompts(self):
        prompts = get_all_system_prompts()
        assert len(prompts) == 6

    def test_keys_are_position_values(self):
        prompts = get_all_system_prompts()
        assert set(prompts.keys()) == {1, 2, 3, 4, 5, 6}

    def test_each_prompt_contains_fused_role(self):
        prompts = get_all_system_prompts()
        for pos_value, prompt in prompts.items():
            pos = YaoPosition(pos_value)
            assert pos.fused_role in prompt


class TestYaoAgentConfig:
    """Tests for YaoAgentConfig dataclass"""

    def test_creation_with_position(self):
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        assert config.position == YaoPosition.INITIAL
        assert config.llm_call is None

    def test_creation_with_llm_call(self):
        def mock_llm(system: str, user: str) -> str:
            return "test"

        config = YaoAgentConfig(position=YaoPosition.SECOND, llm_call=mock_llm)
        assert config.llm_call is not None


class TestYaoAgent:
    """Tests for YaoAgent class"""

    def test_system_prompt_property(self):
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        assert "基础环境层" in agent.system_prompt
        assert "根本" in agent.system_prompt

    def test_analyze_without_llm(self):
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九", "yao_ci": "潜龙勿用"}

        result = agent.analyze(ctx, line_data)

        assert isinstance(result, YaoAnalysis)
        assert result.position == 1
        assert result.line_name == "初九"
        assert result.yao_ci == "潜龙勿用"
        assert "基础环境层" in result.analysis

    def test_analyze_missing_line_name_raises(self):
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"yao_ci": "潜龙勿用"}

        try:
            agent.analyze(ctx, line_data)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "line_name" in str(e)

    def test_analyze_missing_yao_ci_raises(self):
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九"}

        try:
            agent.analyze(ctx, line_data)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "yao_ci" in str(e)

    def test_analyze_with_llm(self):
        def mock_llm(system: str, user: str) -> str:
            return "解读：宜静不宜动\n建议：继续积累\n风险：冒进有险"

        config = YaoAgentConfig(position=YaoPosition.INITIAL, llm_call=mock_llm)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九", "yao_ci": "潜龙勿用"}

        result = agent.analyze(ctx, line_data)

        assert "宜静" in result.analysis
        assert "积累" in result.advice
        assert "险" in result.risks

    def test_each_position_has_unique_fused_role(self):
        agents = {}
        for pos in YaoPosition:
            config = YaoAgentConfig(position=pos)
            agents[pos] = YaoAgent(config)

        fused_roles = [agent.system_prompt for agent in agents.values()]
        for i, pos in enumerate(YaoPosition):
            assert pos.fused_role in fused_roles[i]


class TestYaoAgentOrchestrator:
    """Tests for YaoAgentOrchestrator class"""

    def test_analyze_all_success(self):
        def mock_llm(system: str, user: str) -> str:
            return "解读：测试解读\n建议：测试建议\n风险：测试风险"

        orchestrator = YaoAgentOrchestrator(llm_call=mock_llm)
        ctx = make_hexagram_context()

        results = orchestrator.analyze_all(ctx)

        assert len(results) == 6
        for i, result in enumerate(results, 1):
            assert result.position == i

    def test_analyze_all_no_lines_raises(self):
        orchestrator = YaoAgentOrchestrator()
        ctx = make_hexagram_context(lines=[])

        try:
            orchestrator.analyze_all(ctx)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "No line data" in str(e)

    def test_analyze_all_partial_failure(self):
        call_count = [0]

        def failing_llm(system: str, user: str) -> str:
            call_count[0] += 1
            if call_count[0] in [2, 4]:
                raise ValueError("Simulated failure")
            return "解读：测试\n建议：测试\n风险：测试"

        orchestrator = YaoAgentOrchestrator(llm_call=failing_llm)
        ctx = make_hexagram_context()

        try:
            orchestrator.analyze_all(ctx)
            assert False, "Should have raised PartialFailureError"
        except PartialFailureError as e:
            assert 2 in e.failed_positions
            assert 4 in e.failed_positions
            assert len(e.successful_positions) == 4
            assert len(e.partial_results) == 4

    def test_get_agent_for_position(self):
        orchestrator = YaoAgentOrchestrator()
        agent = orchestrator.get_agent(YaoPosition.FIFTH)
        assert agent.position == YaoPosition.FIFTH
        assert "核心决策层" in agent.system_prompt

    def test_analyze_all_without_llm(self):
        orchestrator = YaoAgentOrchestrator()
        ctx = make_hexagram_context()

        results = orchestrator.analyze_all(ctx)

        assert len(results) == 6
        for result in results:
            assert "待LLM分析" in result.analysis or result.position in range(1, 7)


class TestYaoAgentFusedRoles:
    """Tests verifying all 6 fused role definitions"""

    def test_initial_yao_fused_role(self):
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        prompt = agent.system_prompt

        assert "根本" in prompt, "Should contain traditional meaning"
        assert "环境感知" in prompt, "Should contain modern mapping"
        assert "基础环境层" in prompt, "Should contain fused role"

    def test_second_yao_fused_role(self):
        config = YaoAgentConfig(position=YaoPosition.SECOND)
        agent = YaoAgent(config)
        prompt = agent.system_prompt

        assert "内中馈" in prompt
        assert "资源配置" in prompt
        assert "内部资源层" in prompt

    def test_third_yao_fused_role(self):
        config = YaoAgentConfig(position=YaoPosition.THIRD)
        agent = YaoAgent(config)
        prompt = agent.system_prompt

        assert "君子终日乾乾" in prompt
        assert "风险评估" in prompt
        assert "行动执行层" in prompt

    def test_fourth_yao_fused_role(self):
        config = YaoAgentConfig(position=YaoPosition.FOURTH)
        agent = YaoAgent(config)
        prompt = agent.system_prompt

        assert "门阙" in prompt
        assert "策略执行" in prompt
        assert "关键转折层" in prompt

    def test_fifth_yao_fused_role(self):
        config = YaoAgentConfig(position=YaoPosition.FIFTH)
        agent = YaoAgent(config)
        prompt = agent.system_prompt

        assert "君位" in prompt
        assert "长期规划" in prompt
        assert "核心决策层" in prompt

    def test_top_yao_fused_role(self):
        config = YaoAgentConfig(position=YaoPosition.TOP)
        agent = YaoAgent(config)
        prompt = agent.system_prompt

        assert "亢龙有悔" in prompt
        assert "结果复盘" in prompt
        assert "终局反思层" in prompt


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing modern mapping"""

    def test_role_property_unchanged(self):
        assert YaoPosition.INITIAL.role == "环境感知"
        assert YaoPosition.SECOND.role == "资源配置"
        assert YaoPosition.THIRD.role == "风险评估"
        assert YaoPosition.FOURTH.role == "策略执行"
        assert YaoPosition.FIFTH.role == "长期规划"
        assert YaoPosition.TOP.role == "结果复盘"

    def test_name_cn_property_unchanged(self):
        assert YaoPosition.INITIAL.name_cn == "初爻"
        assert YaoPosition.SECOND.name_cn == "二爻"
        assert YaoPosition.THIRD.name_cn == "三爻"
        assert YaoPosition.FOURTH.name_cn == "四爻"
        assert YaoPosition.FIFTH.name_cn == "五爻"
        assert YaoPosition.TOP.name_cn == "上爻"


class TestYaoAgentEdgeCases:
    """Edge case tests for YaoAgent."""

    def test_analyze_empty_line_data(self):
        """Test analyze with empty line_data dict."""
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {}

        try:
            agent.analyze(ctx, line_data)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "line_name" in str(e) or "yao_ci" in str(e)

    def test_analyze_partial_line_data(self):
        """Test analyze with partial line_data (missing yao_ci)."""
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九"}

        try:
            agent.analyze(ctx, line_data)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "yao_ci" in str(e)

    def test_analyze_llm_returns_empty_string(self):
        """Test analyze when LLM returns empty string."""

        def empty_llm(system: str, user: str) -> str:
            return ""

        config = YaoAgentConfig(position=YaoPosition.INITIAL, llm_call=empty_llm)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九", "yao_ci": "潜龙勿用"}

        result = agent.analyze(ctx, line_data)

        assert result.position == 1
        assert result.line_name == "初九"
        assert result.yao_ci == "潜龙勿用"

    def test_analyze_llm_returns_malformed_response(self):
        """Test analyze when LLM returns malformed response (no proper format)."""

        def malformed_llm(system: str, user: str) -> str:
            return "这不是正确的格式没有换行也没有冒号"

        config = YaoAgentConfig(position=YaoPosition.INITIAL, llm_call=malformed_llm)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九", "yao_ci": "潜龙勿用"}

        result = agent.analyze(ctx, line_data)

        assert result.position == 1
        assert result.analysis is not None

    def test_analyze_with_unicode_in_line_data(self):
        """Test analyze with unicode characters in line data."""
        config = YaoAgentConfig(position=YaoPosition.INITIAL)
        agent = YaoAgent(config)
        ctx = make_hexagram_context()
        line_data = {"line_name": "初九", "yao_ci": "潜龙勿用 🐉"}

        result = agent.analyze(ctx, line_data)

        assert result.position == 1
        assert "🐉" in result.yao_ci


class TestYaoAgentOrchestratorEdgeCases:
    """Edge case tests for YaoAgentOrchestrator."""

    def test_analyze_all_with_mixed_line_data(self):
        """Test analyze_all when some lines have missing data."""

        def mock_llm(system: str, user: str) -> str:
            return "解读：测试\n建议：测试\n风险：测试"

        lines = [
            {"line_name": "初九", "yao_ci": "潜龙勿用"},
            {"line_name": "九二", "yao_ci": "见龙在田"},
            {},  # Missing data
            {"line_name": "九四", "yao_ci": "或跃在渊"},
            {"line_name": "九五", "yao_ci": "飞龙在天"},
            {"line_name": "上九", "yao_ci": "亢龙有悔"},
        ]

        orchestrator = YaoAgentOrchestrator(llm_call=mock_llm)
        ctx = make_hexagram_context(lines=lines)

        try:
            orchestrator.analyze_all(ctx)
            assert False, "Should have raised PartialFailureError"
        except PartialFailureError as e:
            assert 3 in e.failed_positions

    def test_analyze_all_llm_always_fails(self):
        """Test analyze_all when all LLM calls fail with catchable errors."""

        def failing_llm(system: str, user: str) -> str:
            raise ValueError("LLM fails")

        orchestrator = YaoAgentOrchestrator(llm_call=failing_llm)
        ctx = make_hexagram_context()

        try:
            orchestrator.analyze_all(ctx)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "All yao position analyses failed" in str(e)
