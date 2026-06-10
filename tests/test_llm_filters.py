"""Tests for shared LLM output filters."""

from core.llm_filters import filter_think_content


def test_filter_minimax_hlen_hline_block():
    text = "hlen\ninternal reasoning\nhline\n解读：可执行"

    assert filter_think_content(text) == "解读：可执行"


def test_filter_hlen_hlen_block():
    text = "hlen\nhidden chain\nhlen\n建议：稳步推进"

    assert filter_think_content(text) == "建议：稳步推进"


def test_filter_xml_think_block():
    text = "<think>private notes</think>\n风险：控制节奏"

    assert filter_think_content(text) == "风险：控制节奏"


def test_filter_bracket_think_block():
    text = "[think]private notes[/think]\n综合建议：继续验证"

    assert filter_think_content(text) == "综合建议：继续验证"
