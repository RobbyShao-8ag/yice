"""Tests for WebSocket yao streaming helpers."""

from web.backend.routes.websocket import (
    MAX_WEBSOCKET_MESSAGE_BYTES,
    WebSocketMessageTooLarge,
    format_yao_ci_for_display,
    parse_websocket_message,
)


def test_format_yao_ci_for_display_removes_wilhelm_commentary():
    yao_ci = (
        "Hesitation and hindrance.\n"
        "It furthers one to remain persevering.\n\n"
        "【Wilhelm解读】Long English commentary should not appear in the UI badge."
    )

    result = format_yao_ci_for_display(yao_ci)

    assert "Wilhelm" not in result
    assert "Hesitation and hindrance" in result
    assert "\n" not in result


def test_format_yao_ci_for_display_truncates_long_text():
    result = format_yao_ci_for_display("a" * 120)

    assert len(result) <= 83
    assert result.endswith("...")


def test_parse_websocket_message_rejects_large_payload():
    oversized_payload = "{" + '"x":"' + ("a" * MAX_WEBSOCKET_MESSAGE_BYTES) + '"}'

    try:
        parse_websocket_message(oversized_payload)
        assert False, "Expected WebSocketMessageTooLarge"
    except WebSocketMessageTooLarge:
        pass
