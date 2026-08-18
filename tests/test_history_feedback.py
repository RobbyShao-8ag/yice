import json

import pytest
from fastapi import HTTPException

from web.backend.routes import history


@pytest.mark.asyncio
async def test_history_feedback_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_DIR", tmp_path)
    created = await history.create_history(
        {
            "question": "是否推进项目？",
            "hexagram": {"id": 3, "name": "屯"},
            "yao_analysis": [],
            "report": {"decision_tendency": "有条件推进"},
        }
    )
    result = await history.update_history_feedback(
        created["id"],
        {
            "decision_taken": "先验证14天",
            "outcome": "一位客户付费",
            "usefulness_rating": 5,
            "notes": "停止条件很有用",
        },
    )
    assert result["feedback"]["usefulness_rating"] == 5
    record = json.loads((tmp_path / f"{created['id']}.json").read_text(encoding="utf-8"))
    assert record["feedback"]["decision_taken"] == "先验证14天"
    assert record["feedback"]["reviewed_at"]


@pytest.mark.asyncio
async def test_history_feedback_rejects_invalid_rating(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_DIR", tmp_path)
    created = await history.create_history(
        {
            "question": "测试",
            "hexagram": {},
            "yao_analysis": [],
            "report": {},
        }
    )
    with pytest.raises(HTTPException) as exc:
        await history.update_history_feedback(
            created["id"], {"usefulness_rating": 6}
        )
    assert exc.value.status_code == 400
