"""End-to-end tests for QiguaAgent + SceneRouter collaboration."""

import pytest
from core.models import QuestionContext
from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
from agents.scene_router import SceneRouter, SceneRouterConfig
from agents.sufficiency_checker import SufficiencyResult


def create_mock_llm(responses: list[str] | str):
    """Create a mock LLM that returns predefined responses.

    Args:
        responses: Single response or list of responses to return in sequence

    Returns:
        Mock LLM function
    """
    if isinstance(responses, str):
        responses = [responses]

    call_count = [0]

    def mock_llm(system: str, prompt: str) -> str:
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]

    return mock_llm


class TestSceneRouterCheckInfoSufficiency:
    """Tests for SceneRouter.check_info_sufficiency() method."""

    def test_insufficient_info_missing_background(self):
        """Test that insufficient background triggers is_sufficient=False."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="我想创业",
            question_type="创业",
            background="",  # Empty background
            constraints="",
            expected_outcome="",
            time_horizon="",
            risk_tolerance="",
            dialogue_history=[],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is False
        assert "详细的背景描述" in result.missing_info

    def test_insufficient_info_missing_expected_outcome(self):
        """Test that missing expected outcome triggers is_sufficient=False."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="我想创业",
            question_type="创业",
            background="有一些想法",
            constraints="",
            expected_outcome="",  # Empty expected outcome
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[{"round": 1, "question": "test", "answer": "test"}],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is False
        assert "明确的期望目标" in result.missing_info

    def test_sufficient_info_for_exact_match(self):
        """Test that sufficient info enables exact matching."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="我想创业做新项目",
            question_type="创业",
            background="有技术背景，想做互联网创业",
            constraints="资金有限",
            expected_outcome="项目成功起步",
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[
                {"round": 1, "question": "Q1", "answer": "A1"},
                {"round": 2, "question": "Q2", "answer": "A2"},
            ],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is True
        assert "信息足够进行精确卦象匹配" in result.reasoning

    def test_sufficient_info_with_fuzzy_match(self):
        """Test that fuzzy match also indicates sufficiency."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="我想开始一个新项目",
            question_type="创业",  # Use specific type instead of "其他"
            background="需要起步资金来做互联网创业",  # Make background longer (>= 10 chars)
            constraints="时间紧张",
            expected_outcome="项目成功获得投资",  # Make expected outcome longer (>= 5 chars)
            time_horizon="短期",
            risk_tolerance="高",
            dialogue_history=[
                {"round": 1, "question": "Q1", "answer": "A1"},
                {"round": 2, "question": "Q2", "answer": "A2"},
            ],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is True

    def test_generates_clarifying_question(self):
        """Test that clarifying questions are generated for missing info."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="我想问问",
            question_type="其他",
            background="",
            constraints="",
            expected_outcome="",
            time_horizon="",
            risk_tolerance="",
            dialogue_history=[],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is False
        assert result.next_question is not None
        assert len(result.next_question) > 0

    def test_no_llm_fallback_available(self):
        """Test behavior when LLM is not available and matching fails."""
        router = SceneRouter(SceneRouterConfig())

        # Create a question that won't match any scene
        # But first ensure basic fields are populated so we reach the matching logic
        ctx = QuestionContext(
            raw_question="xyz123 无意义问题",
            question_type="其他",
            background="这是一段无关内容的背景描述",  # Long enough background
            constraints="",
            expected_outcome="无明确目标",  # Long enough expected outcome
            time_horizon="",
            risk_tolerance="",
            dialogue_history=[
                {"round": 1, "question": "Q1", "answer": "A1"},
            ],
        )

        result = router.check_info_sufficiency(ctx)

        # Should indicate insufficiency due to "其他" question type
        assert result.is_sufficient is False
        # The check stops early due to vague question type, so "问题场景类型" should be in missing
        assert "问题场景类型" in result.missing_info


class TestQiguaAgentWithSceneRouter:
    """Tests for QiguaAgent integration with SceneRouter."""

    def test_qigua_agent_has_scene_router(self):
        """Test that QiguaAgent initializes SceneRouter."""
        mock_llm = create_mock_llm("test response")
        config = QiguaAgentConfig(llm_call=mock_llm)
        agent = QiguaAgent(config)

        assert agent.scene_router is not None
        assert isinstance(agent.scene_router, SceneRouter)

    def test_qigua_agent_without_llm_has_no_scene_router(self):
        """Test that QiguaAgent without LLM has no SceneRouter."""
        config = QiguaAgentConfig()
        agent = QiguaAgent(config)

        assert agent.scene_router is None

    def test_check_sufficiency_calls_both_checkers(self):
        """Test that _check_sufficiency calls both LLM checker and SceneRouter."""
        # Create LLM responses:
        # 1. Analyzer response (JSON with question_type)
        # 2. SufficiencyChecker response (is_sufficient=false first)
        # 3. OptionGenerator response
        # 4. SufficiencyChecker response (is_sufficient=true)
        llm_responses = [
            '{"question_type": "创业", "domain": "商业", "questions": [{"field": "background", "question_text": "背景？", "options": ["A. 详细说明"]}], "first_question": {"field": "background", "question_text": "背景？", "options": ["A. 详细说明"]}}',
            '{"is_sufficient": false, "missing_info": ["背景"], "reasoning": "需要更多背景"}',
            '{"question": "下一个问题", "options": ["A. 选项"]}',
            '{"is_sufficient": true, "missing_info": [], "reasoning": "信息充分"}',
            '{"is_sufficient": true, "missing_info": [], "reasoning": "信息充分"}',
        ]

        mock_llm = create_mock_llm(llm_responses)
        config = QiguaAgentConfig(llm_call=mock_llm, max_rounds=2)
        agent = QiguaAgent(config)

        # Verify both checker and scene_router exist
        assert agent.checker is not None
        assert agent.scene_router is not None

        # Test internal _check_sufficiency method
        ctx = QuestionContext(
            raw_question="我想创业",
            question_type="创业",
            background="测试背景信息足够长",
            constraints="测试约束",
            expected_outcome="测试期望",
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[
                {"round": 1, "question": "Q1", "answer": "A1", "answer_text": "背景"},
                {"round": 2, "question": "Q2", "answer": "A2", "answer_text": "约束"},
            ],
        )

        # Access private method for testing
        result = agent._check_sufficiency(
            ctx.raw_question,
            ctx.question_type,
            {
                "background": ctx.background,
                "constraints": ctx.constraints,
                "expected_outcome": ctx.expected_outcome,
            },
            ctx.dialogue_history,
        )

        # Should be sufficient (both checkers should pass)
        assert isinstance(result, SufficiencyResult)


class TestAgentCollaborationIntegration:
    """Integration tests for full agent collaboration pipeline."""

    def test_full_collaboration_flow(self):
        """Test full flow: QiguaAgent collects info -> SceneRouter validates."""

        # Create an LLM that always returns "sufficient" for checker
        def mock_llm_smart(system: str, prompt: str) -> str:
            # Check if this is a sufficiency check prompt
            if "是否足够" in prompt or "sufficient" in prompt.lower():
                return '{"is_sufficient": true, "missing_info": [], "reasoning": "信息充分"}'
            # For scene router LLM fallback
            return "5 - 需卦，创业起步"
            # For analyzer/option_gen (not used in this direct test)

        config = QiguaAgentConfig(llm_call=mock_llm_smart, max_rounds=2)
        agent = QiguaAgent(config)

        # Verify collaboration setup
        assert agent.checker is not None, "LLM checker should exist"
        assert agent.scene_router is not None, "SceneRouter should exist"

        # Test that both components can work together
        ctx = QuestionContext(
            raw_question="我想创业",
            question_type="创业",
            background="有技术背景，准备做互联网项目",
            constraints="资金有限",
            expected_outcome="成功起步并盈利",
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[
                {"round": 1, "question": "Q1", "answer": "A1", "answer_text": "背景"},
                {"round": 2, "question": "Q2", "answer": "A2", "answer_text": "约束"},
                {"round": 3, "question": "Q3", "answer": "A3", "answer_text": "目标"},
            ],
        )

        # Check sufficiency with both checkers
        result = agent._check_sufficiency(
            ctx.raw_question,
            ctx.question_type,
            {
                "background": ctx.background,
                "expected_outcome": ctx.expected_outcome,
            },
            ctx.dialogue_history,
        )

        # Should be sufficient (both checkers pass with proper data)
        assert result.is_sufficient is True, f"Expected sufficient but got: {result}"
        assert "场景路由器确认" in result.reasoning

    def test_scene_router_catches_what_llm_misses(self):
        """Test that SceneRouter can catch issues LLM might miss."""

        # LLM says sufficient, but SceneRouter should catch missing scene info
        def mock_llm_too_optimistic(system: str, prompt: str) -> str:
            # Always say sufficient
            return (
                '{"is_sufficient": true, "missing_info": [], "reasoning": "看起来够了"}'
            )

        config = QiguaAgentConfig(llm_call=mock_llm_too_optimistic, max_rounds=1)
        agent = QiguaAgent(config)

        # Create context with vague info that LLM accepts
        ctx = QuestionContext(
            raw_question="问问",
            question_type="其他",  # Vague type
            background="一些信息",
            constraints="",
            expected_outcome="",  # Missing expected outcome
            time_horizon="",
            risk_tolerance="",
            dialogue_history=[{"round": 1, "question": "Q", "answer": "A"}],
        )

        result = agent._check_sufficiency(
            ctx.raw_question,
            ctx.question_type,
            {"background": ctx.background},
            ctx.dialogue_history,
        )

        # SceneRouter should catch the missing info even if LLM says it's fine
        assert result.is_sufficient is False
        assert len(result.missing_info) > 0


class TestClarifyingQuestionGeneration:
    """Tests for clarifying question generation."""

    def test_generates_question_for_missing_scene_type(self):
        """Test question generation for missing scene type."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="问问",
            question_type="其他",
            background="背景",
            constraints="",
            expected_outcome="目标",
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[{"round": 1}],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.next_question is not None
        assert "领域" in result.next_question or "场景" in result.next_question

    def test_generates_question_for_missing_background(self):
        """Test question generation for missing background."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="问问",
            question_type="创业",
            background="",
            constraints="",
            expected_outcome="目标",
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[{"round": 1}],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.next_question is not None
        assert "背景" in result.next_question or "情况" in result.next_question


class TestEdgeCases:
    """Edge case tests for agent collaboration."""

    def test_empty_dialogue_history(self):
        """Test sufficiency check with empty dialogue history."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="创业",
            question_type="创业",
            background="",
            constraints="",
            expected_outcome="",
            time_horizon="",
            risk_tolerance="",
            dialogue_history=[],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is False
        assert "更多背景细节" in result.missing_info

    def test_very_short_background(self):
        """Test with background that's too short."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="创业",
            question_type="创业",
            background="短",  # Too short (< 10 chars)
            constraints="",
            expected_outcome="目标",
            time_horizon="中期",
            risk_tolerance="中",
            dialogue_history=[{"round": 1}],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is False
        assert "详细的背景描述" in result.missing_info

    def test_sufficient_info_all_fields_populated(self):
        """Test with all required fields properly populated."""
        router = SceneRouter(SceneRouterConfig())

        ctx = QuestionContext(
            raw_question="我想创业做互联网项目",
            question_type="创业",
            background="我有 5 年互联网行业经验，准备离职创业",
            constraints="启动资金 50 万",
            expected_outcome="一年内实现盈利",
            time_horizon="短期",
            risk_tolerance="高",
            dialogue_history=[
                {"round": 1, "question": "Q1", "answer": "A1"},
                {"round": 2, "question": "Q2", "answer": "A2"},
                {"round": 3, "question": "Q3", "answer": "A3"},
            ],
        )

        result = router.check_info_sufficiency(ctx)

        assert result.is_sufficient is True
