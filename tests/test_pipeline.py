"""
Tests for core/pipeline.py - PipelineContext and stage validators.
"""

import pytest

from core.models import HexagramContext, QuestionContext, YaoAnalysis
from core.pipeline import (
    PipelineContext,
    ValidationError,
    validate_hexagram_context,
    validate_question_context,
    validate_yao_analyses,
    validate_stage_transition,
    VALID_STAGES,
)


class TestPipelineContextCreation:
    def test_default_initialization(self):
        ctx = PipelineContext()
        assert ctx.session_id is not None
        assert len(ctx.session_id) == 8
        assert ctx.current_stage == "init"
        assert ctx.accumulated_outputs == {}
        assert ctx.error_log == []

    def test_custom_session_id(self):
        ctx = PipelineContext(session_id="custom123")
        assert ctx.session_id == "custom123"

    def test_custom_initial_stage(self):
        ctx = PipelineContext(current_stage="qigua")
        assert ctx.current_stage == "qigua"


class TestPipelineContextCheckpointRollback:
    def test_checkpoint_returns_id(self):
        ctx = PipelineContext()
        cp_id = ctx.checkpoint()
        assert cp_id.startswith("cp_")

    def test_rollback_restores_state(self):
        ctx = PipelineContext(current_stage="init")
        ctx.accumulated_outputs["test"] = "value1"
        ctx.checkpoint()

        ctx.accumulated_outputs["test"] = "value2"
        ctx.current_stage = "qigua"

        success = ctx.rollback()
        assert success
        assert ctx.accumulated_outputs["test"] == "value1"
        assert ctx.current_stage == "init"

    def test_rollback_to_specific_checkpoint(self):
        ctx = PipelineContext()
        ctx.accumulated_outputs["v"] = 1
        cp1 = ctx.checkpoint()

        ctx.accumulated_outputs["v"] = 2
        cp2 = ctx.checkpoint()

        ctx.accumulated_outputs["v"] = 3

        ctx.rollback(cp1)
        assert ctx.accumulated_outputs["v"] == 1

    def test_rollback_with_no_checkpoints(self):
        ctx = PipelineContext()
        success = ctx.rollback()
        assert success is False

    def test_rollback_invalid_checkpoint_id(self):
        ctx = PipelineContext()
        ctx.checkpoint()
        success = ctx.rollback("cp_999")
        assert success is False


class TestPipelineContextErrorLogging:
    def test_log_error(self):
        ctx = PipelineContext()
        ctx.log_error("qigua", "LLMError", "API timeout")
        assert len(ctx.error_log) == 1
        assert ctx.error_log[0]["stage"] == "qigua"
        assert ctx.error_log[0]["error_type"] == "LLMError"

    def test_log_error_with_details(self):
        ctx = PipelineContext()
        ctx.log_error("scene_router", "DataError", "Missing hexagram", {"id": 99})
        assert ctx.error_log[0]["details"] == {"id": 99}


class TestPipelineContextStageAdvance:
    def test_advance_to_valid_stage(self):
        ctx = PipelineContext(current_stage="init")
        result = ctx.advance_stage("qigua")
        assert result is True
        assert ctx.current_stage == "qigua"

    def test_advance_to_invalid_stage(self):
        ctx = PipelineContext()
        with pytest.raises(ValueError, match="Invalid stage"):
            ctx.advance_stage("invalid_stage")


class TestValidateQuestionContext:
    def test_valid_question_context(self):
        ctx = QuestionContext(
            raw_question="Should I quit my job?",
            question_type="职业选择",
            background="5 years at current company",
            constraints="Need income stability",
            expected_outcome="Career growth",
            time_horizon="3 months",
            risk_tolerance="中",
        )
        is_valid, missing = validate_question_context(ctx)
        assert is_valid is True
        assert missing == []

    def test_valid_question_context_dict(self):
        ctx_dict = {
            "raw_question": "Should I invest?",
            "question_type": "投资判断",
            "background": "Have savings",
            "constraints": "Conservative",
            "expected_outcome": "Growth",
            "time_horizon": "1 year",
            "risk_tolerance": "低",
        }
        is_valid, missing = validate_question_context(ctx_dict)
        assert is_valid is True

    def test_missing_fields(self):
        ctx = QuestionContext(
            raw_question="Test",
            question_type="",
            background="",
            constraints="",
            expected_outcome="",
            time_horizon="",
            risk_tolerance="",
        )
        is_valid, missing = validate_question_context(ctx)
        assert is_valid is False
        assert "question_type" in missing
        assert "background" in missing

    def test_none_values_treated_as_missing(self):
        ctx_dict = {
            "raw_question": "Test",
            "question_type": None,
            "background": "ok",
            "constraints": "ok",
            "expected_outcome": "ok",
            "time_horizon": "ok",
            "risk_tolerance": "ok",
        }
        is_valid, missing = validate_question_context(ctx_dict)
        assert is_valid is False
        assert "question_type" in missing


class TestValidateHexagramContext:
    def test_valid_hexagram_context(self):
        question = QuestionContext(
            raw_question="Test",
            question_type="其他",
            background="test",
            constraints="test",
            expected_outcome="test",
            time_horizon="test",
            risk_tolerance="中",
        )
        ctx = HexagramContext(
            question=question,
            hexagram_id=1,
            hexagram_name="乾",
            match_reason="Test match",
            hexagram_data={"id": 1, "lines": [1, 1, 1, 1, 1, 1]},
        )
        is_valid, missing = validate_hexagram_context(ctx)
        assert is_valid is True

    def test_missing_hexagram_id(self):
        ctx_dict = {
            "hexagram_name": "乾",
            "hexagram_data": {"lines": []},
        }
        is_valid, missing = validate_hexagram_context(ctx_dict)
        assert is_valid is False
        assert "hexagram_id" in missing

    def test_missing_lines_in_hexagram_data(self):
        ctx_dict = {
            "hexagram_id": 1,
            "hexagram_name": "乾",
            "hexagram_data": {},
        }
        is_valid, missing = validate_hexagram_context(ctx_dict)
        assert is_valid is False
        assert "hexagram_data.lines" in missing


class TestValidateYaoAnalyses:
    def test_valid_six_yao_analyses(self):
        analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci=f"爻辞{i}",
                analysis=f"分析{i}",
                advice=f"建议{i}",
                risks=f"风险{i}",
            )
            for i in range(1, 7)
        ]
        is_valid, missing = validate_yao_analyses(analyses)
        assert is_valid is True
        assert missing == []

    def test_valid_dict_analyses(self):
        analyses = [
            {
                "position": i,
                "line_name": f"九{i}",
                "yao_ci": f"爻辞{i}",
                "analysis": f"分析{i}",
                "advice": f"建议{i}",
                "risks": f"风险{i}",
            }
            for i in range(1, 7)
        ]
        is_valid, missing = validate_yao_analyses(analyses)
        assert is_valid is True

    def test_empty_analyses_list(self):
        is_valid, missing = validate_yao_analyses([])
        assert is_valid is False
        assert "all positions (empty list)" in missing

    def test_wrong_number_of_analyses(self):
        analyses = [
            YaoAnalysis(
                position=1,
                line_name="初九",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            )
        ]
        is_valid, missing = validate_yao_analyses(analyses)
        assert is_valid is False
        assert "expected 6 analyses" in missing[0]

    def test_missing_positions(self):
        analyses = [
            YaoAnalysis(
                position=i,
                line_name=f"九{i}",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            )
            for i in [1, 2, 3, 5, 6]
        ]
        is_valid, missing = validate_yao_analyses(analyses)
        assert is_valid is False
        assert len(analyses) == 5
        assert "expected 6 analyses" in missing[0]

    def test_missing_analysis_fields(self):
        analyses = [
            YaoAnalysis(
                position=1,
                line_name="",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            ),
            YaoAnalysis(
                position=2,
                line_name="九二",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            ),
            YaoAnalysis(
                position=3,
                line_name="九三",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            ),
            YaoAnalysis(
                position=4,
                line_name="九四",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            ),
            YaoAnalysis(
                position=5,
                line_name="九五",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            ),
            YaoAnalysis(
                position=6,
                line_name="上九",
                yao_ci="a",
                analysis="b",
                advice="c",
                risks="d",
            ),
        ]
        is_valid, missing = validate_yao_analyses(analyses)
        assert is_valid is False
        assert any("line_name" in m for m in missing)


class TestValidateStageTransition:
    def test_valid_forward_transition(self):
        assert validate_stage_transition("init", "qigua") is True
        assert validate_stage_transition("qigua", "scene_router") is True
        assert validate_stage_transition("scene_router", "yao_analysis") is True
        assert validate_stage_transition("yao_analysis", "reporter") is True
        assert validate_stage_transition("reporter", "complete") is True

    def test_same_stage_transition(self):
        assert validate_stage_transition("init", "init") is True
        assert validate_stage_transition("qigua", "qigua") is True

    def test_invalid_skip_transition(self):
        assert validate_stage_transition("init", "scene_router") is False
        assert validate_stage_transition("init", "complete") is False

    def test_invalid_backward_transition(self):
        assert validate_stage_transition("qigua", "init") is False
        assert validate_stage_transition("complete", "reporter") is False

    def test_invalid_stage_names(self):
        assert validate_stage_transition("invalid", "qigua") is False
        assert validate_stage_transition("init", "invalid") is False
