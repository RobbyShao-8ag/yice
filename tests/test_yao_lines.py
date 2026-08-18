import pytest

from core.yao_lines import get_yao_name, get_yao_values


def test_get_yao_name_for_qian_and_kun():
    assert [get_yao_name(i, [1] * 6) for i in range(1, 7)] == [
        "初九", "九二", "九三", "九四", "九五", "上九"
    ]
    assert [get_yao_name(i, [0] * 6) for i in range(1, 7)] == [
        "初六", "六二", "六三", "六四", "六五", "上六"
    ]


def test_get_yao_values_prefers_binary_code():
    data = {
        "binary_code": [1, 0, 1, 0, 1, 0],
        "lines": [{"line_name": "初六"}] * 6,
    }
    assert get_yao_values(data) == [1, 0, 1, 0, 1, 0]


def test_get_yao_name_rejects_invalid_input():
    with pytest.raises(ValueError):
        get_yao_name(0, [1] * 6)
    with pytest.raises(ValueError):
        get_yao_name(1, [1, 0])
