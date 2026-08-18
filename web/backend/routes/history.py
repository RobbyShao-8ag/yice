import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

# 历史记录保存目录
HISTORY_DIR = Path(__file__).parent.parent.parent / "history"


def _ensure_history_dir() -> None:
    """Ensure history directory exists."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/")
async def list_history(limit: int = 20) -> dict[str, Any]:
    """List recent decision reports."""
    _ensure_history_dir()

    if not HISTORY_DIR.exists():
        return {"history": [], "total": 0}

    files = sorted(
        [f for f in HISTORY_DIR.glob("*.json") if f.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )[:limit]

    history = []
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            history.append(
                {
                    "id": file.stem,
                    "filename": file.name,
                    "question": data.get("question", ""),
                    "hexagram": data.get("hexagram", {}).get("name", ""),
                    "created_at": data.get(
                        "created_at",
                        datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                    ),
                }
            )
        except (json.JSONDecodeError, KeyError):
            # 如果文件损坏，只返回基本信息
            history.append(
                {
                    "id": file.stem,
                    "filename": file.name,
                    "question": "",
                    "hexagram": "",
                    "created_at": datetime.fromtimestamp(
                        file.stat().st_mtime
                    ).isoformat(),
                }
            )

    return {"history": history, "total": len(history)}


@router.get("/{report_id}")
async def get_history(report_id: str) -> dict[str, Any]:
    """Get a specific decision report."""
    file_path = HISTORY_DIR / f"{report_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        return {
            "id": report_id,
            "content": content,
            "created_at": content.get(
                "created_at",
                datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            ),
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="报告文件损坏")


@router.delete("/{report_id}")
async def delete_history(report_id: str) -> dict[str, str]:
    """Delete a decision report."""
    file_path = HISTORY_DIR / f"{report_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    os.remove(file_path)
    return {"message": "报告已删除"}


@router.post("/")
async def create_history(record: dict[str, Any]) -> dict[str, Any]:
    """Create a new decision report."""
    _ensure_history_dir()

    # Validate required fields
    required_fields = ["question", "hexagram", "yao_analysis", "report"]
    for field in required_fields:
        if field not in record:
            raise HTTPException(status_code=400, detail=f"缺少必要字段：{field}")

    # Generate filename from timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = HISTORY_DIR / f"{timestamp}.json"

    # Add metadata
    record["created_at"] = datetime.now().isoformat()
    record["id"] = timestamp

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return {
            "status": "ok",
            "id": timestamp,
            "message": "历史记录已保存",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")


@router.patch("/{report_id}/feedback")
async def update_history_feedback(
    report_id: str, feedback: dict[str, Any]
) -> dict[str, Any]:
    """Record what the user chose and what happened afterwards."""
    file_path = HISTORY_DIR / f"{report_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    rating = feedback.get("usefulness_rating")
    if rating is not None and (not isinstance(rating, int) or not 1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="usefulness_rating 必须是 1-5 的整数")

    allowed = {
        "decision_taken",
        "outcome",
        "usefulness_rating",
        "notes",
    }
    cleaned = {
        key: value
        for key, value in feedback.items()
        if key in allowed and isinstance(value, (str, int))
    }
    cleaned["reviewed_at"] = datetime.now().isoformat()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            record = json.load(f)
        record["feedback"] = cleaned
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "id": report_id, "feedback": cleaned}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="报告文件损坏")
