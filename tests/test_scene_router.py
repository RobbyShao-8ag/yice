"""Tests for SceneRouter with fallback strategies."""

import pytest
from core.models import HexagramContext, QuestionContext
from agents.scene_router import (
    SceneRouter,
    SceneRouterConfig,
    DEFAULT_SCENE_MAPPING,
    FALLBACK_HEXAGRAM,
)


def create_question(
    question_type="其他",
    raw_question="测试问题",
    background="测试背景",
    expected_outcome="测试期望",
) -> QuestionContext:
    """Helper to create QuestionContext for testing."""
    return QuestionContext(
        raw_question=raw_question,
        question_type=question_type,
        background=background,
        constraints="测试约束",
        expected_outcome=expected_outcome,
        time_horizon="短期",
        risk_tolerance="中",
    )


def test_scene_router_config_defaults():
    """Test SceneRouterConfig default values."""
    config = SceneRouterConfig()
    assert config.llm_call is None
    assert config.fuzzy_threshold == 0.3
    assert config.scene_mapping_path is None


def test_scene_router_config_custom():
    """Test SceneRouterConfig with custom values."""
    mock_llm = lambda s, p: "response"
    config = SceneRouterConfig(
        llm_call=mock_llm,
        fuzzy_threshold=0.5,
        scene_mapping_path="/path/to/mapping.json",
    )
    assert config.llm_call is mock_llm
    assert config.fuzzy_threshold == 0.5
    assert config.scene_mapping_path == "/path/to/mapping.json"


def test_exact_match_by_question_type():
    """Test Layer 1: Exact match by question_type."""
    config = SceneRouterConfig()
    router = SceneRouter(config)

    question = create_question(question_type="创业")
    result = router.route(question)

    assert isinstance(result, HexagramContext)
    assert result.hexagram_id == 5  # 需卦
    assert result.hexagram_name == "需卦"
    assert "EXACT" in result.match_reason


def test_exact_match_by_keyword():
    """Test Layer 1: Exact match by keyword in question text."""
    config = SceneRouterConfig()
    router = SceneRouter(config)

    question = create_question(
        question_type="其他",
        raw_question="我想创业做点新项目",
    )
    result = router.route(question)

    assert isinstance(result, HexagramContext)
    assert result.hexagram_id == 5
    assert "EXACT" in result.match_reason


def test_fuzzy_match():
    """Test Layer 2: Fuzzy keyword matching."""
    config = SceneRouterConfig(fuzzy_threshold=0.3)
    router = SceneRouter(config)

    # Use keywords that will trigger fuzzy match with "创业"
    question = create_question(
        question_type="其他",
        raw_question="我想开始一个新项目",
        background="需要起步资金",
        expected_outcome="项目成功",
    )
    result = router.route(question)

    assert isinstance(result, HexagramContext)
    assert result.hexagram_id == 5  # Should match 创业 (keywords: 创业, 起步, 新项目)
    assert "FUZZY" in result.match_reason


def test_fuzzy_match_below_threshold():
    """Test that fuzzy match doesn't trigger below threshold."""
    config = SceneRouterConfig(fuzzy_threshold=0.9)
    router = SceneRouter(config)

    question = create_question(
        question_type="其他",
        raw_question="一些无关的问题",
    )
    result = router.route(question)

    # Should fall back to default
    assert isinstance(result, HexagramContext)
    assert result.hexagram_id == 1


def test_llm_fallback():
    """Test Layer 3: LLM fallback when exact and fuzzy fail."""
    mock_llm = lambda s, p: "25 - 天雷无妄，适合避免意外"

    config = SceneRouterConfig(llm_call=mock_llm)
    router = SceneRouter(config)

    # Use a question that won't match any fuzzy keywords
    question = create_question(
        question_type="其他",
        raw_question="今天天气真好",
    )
    result = router.route(question)

    assert isinstance(result, HexagramContext)
    assert result.hexagram_id == 25
    assert "LLM" in result.match_reason


def test_llm_fallback_parses_number():
    """Test that LLM fallback correctly parses hexagram number."""
    mock_llm = lambda s, p: "11. 建议使用地天泰"

    config = SceneRouterConfig(llm_call=mock_llm)
    router = SceneRouter(config)

    question = create_question(question_type="其他")
    result = router.route(question)

    assert result.hexagram_id == 11


def test_fallback_when_no_llm():
    """Test fallback when LLM is not available and fuzzy fails."""
    config = SceneRouterConfig()
    router = SceneRouter(config)

    # Use a question that won't match anything
    question = create_question(
        question_type="其他",
        raw_question="xyz123 nonsense",
    )
    result = router.route(question)

    assert isinstance(result, HexagramContext)
    assert result.hexagram_id == FALLBACK_HEXAGRAM["hexagram_id"]
    assert "fallback" in result.match_reason.lower()


def test_route_preserves_question_context():
    """Test that route preserves original question context."""
    config = SceneRouterConfig()
    router = SceneRouter(config)

    question = create_question(
        question_type="投资",
        raw_question="如何理财",
        background="有闲置资金",
        expected_outcome="资产增值",
    )
    result = router.route(question)

    assert result.question == question


def test_hexagram_context_fields():
    """Test that HexagramContext has all required fields."""
    config = SceneRouterConfig()
    router = SceneRouter(config)

    question = create_question()
    result = router.route(question)

    assert result.hexagram_id is not None
    assert result.hexagram_name is not None
    assert result.match_reason is not None
    assert result.hexagram_data is not None
    assert isinstance(result.hexagram_data, dict)


def test_llm_fallback_hexagram_name_uses_data_loader():
    """LLM fallback should prefer canonical data over hardcoded names."""

    class FakeLoader:
        def get_hexagram(self, hexagram_id):
            return {"id": hexagram_id, "name": "数据卦名"}

        def get_lines_for_hexagram(self, hexagram_id):
            return []

    router = SceneRouter(
        SceneRouterConfig(
            llm_call=lambda _system, _user: "5 因为需要等待时机",
            data_loader=FakeLoader(),
        )
    )

    question = create_question(question_type="其他", raw_question="完全未知的新场景")
    result = router.route(question)

    assert result.hexagram_id == 5
    assert result.hexagram_name == "数据卦名"


def test_default_scene_mapping_coverage():
    """Test that default scene mapping covers key scenarios."""
    expected_keys = [
        "创业",
        "职业选择",
        "投资",
        "人际关系",
        "学业",
        "搬家",
        "婚恋",
        "健康",
    ]
    for key in expected_keys:
        assert key in DEFAULT_SCENE_MAPPING
        assert "hexagram_id" in DEFAULT_SCENE_MAPPING[key]
        assert "hexagram_name" in DEFAULT_SCENE_MAPPING[key]
        assert "keywords" in DEFAULT_SCENE_MAPPING[key]


def test_fuzzy_threshold_parameter():
    """Test fuzzy_threshold parameter affects matching."""
    config_low = SceneRouterConfig(fuzzy_threshold=0.1)
    router_low = SceneRouter(config_low)

    config_high = SceneRouterConfig(fuzzy_threshold=0.9)
    router_high = SceneRouter(config_high)

    question = create_question(
        raw_question="关于职业发展的问题",
    )

    result_low = router_low.route(question)
    result_high = router_high.route(question)

    # Lower threshold should match more
    assert result_low.hexagram_id == 26  # Should match 职业
    # Higher threshold might not match and falls back
    assert result_high.hexagram_id == FALLBACK_HEXAGRAM["hexagram_id"]


# Edge case tests for SceneRouter
class TestSceneRouterEdgeCases:
    """Edge case tests for SceneRouter."""

    def test_out_of_range_hexagram_id_in_mapping(self):
        """Test handling when scene mapping contains invalid hexagram_id."""
        invalid_mapping = {
            "test_keyword": {
                "hexagram_id": 999,
                "hexagram_name": "无效卦",
                "keywords": ["test"],
            }
        }

        config = SceneRouterConfig(scene_mapping_path=None)
        router = SceneRouter(config)

        original_mapping = router._scene_mapping
        router._scene_mapping = invalid_mapping

        question = create_question(
            question_type="其他",
            raw_question="test_keyword something",
        )
        result = router.route(question)

        assert result.hexagram_id == 999
        assert result.hexagram_name == "无效卦"

        router._scene_mapping = original_mapping

    def test_empty_hexagram_data(self):
        """Test routing when hexagram_data is empty."""
        config = SceneRouterConfig()
        router = SceneRouter(config)

        question = create_question(question_type="其他")
        result = router.route(question)

        # Should still return valid result with empty or minimal hexagram_data
        assert result.hexagram_data is not None

    def test_llm_fallback_returns_invalid_number(self):
        """Test behavior when LLM returns non-parseable response."""
        mock_llm = lambda s, p: "这是无效响应没有数字"

        config = SceneRouterConfig(llm_call=mock_llm)
        router = SceneRouter(config)

        question = create_question(question_type="其他")
        result = router.route(question)

        # Should fall back to default when number can't be parsed
        assert result.hexagram_id == FALLBACK_HEXAGRAM["hexagram_id"]

    def test_question_context_with_none_fields(self):
        """Test routing with QuestionContext having None optional fields."""
        question = QuestionContext(
            raw_question="测试",
            question_type="",
            background="",
            constraints="",
            expected_outcome="",
            time_horizon="",
            risk_tolerance="",
        )

        config = SceneRouterConfig()
        router = SceneRouter(config)

        result = router.route(question)

        assert result.hexagram_id is not None
        assert result.question is not None
