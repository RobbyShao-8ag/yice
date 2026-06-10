"""Tests for QiguaAgent internals."""

from agents.qigua_agent import QiguaAgent


def test_infer_field_fallback_is_stable_per_question_not_config_size():
    agent = QiguaAgent()

    first = agent._infer_field("请补充其他重要信息")
    second = agent._infer_field("还有哪些补充判断")

    assert first == "info_1"
    assert second == "info_2"
    assert first != second
