import json
from pathlib import Path

import pytest

from agents.scene_router import SceneRouter, SceneRouterConfig
from core.data_loader import DataLoader, DataLoaderConfig
from main import build_question_context


ROOT = Path(__file__).parent.parent


def load_cases():
    return json.loads((ROOT / "data" / "evaluation_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_local_router_matches_acceptable_hexagram(case):
    loader = DataLoader(DataLoaderConfig(data_dir=str(ROOT / "data")))
    router = SceneRouter(
        SceneRouterConfig(
            scene_mapping_path=str(ROOT / "data" / "scene_mapping.json"),
            data_loader=loader,
        )
    )
    context = build_question_context(case["question"], None)
    result = router.route(context)
    assert result.hexagram_id in case["acceptable_hexagrams"], (
        f"{case['id']} routed to {result.hexagram_id} ({result.match_reason}); "
        f"acceptable={case['acceptable_hexagrams']}"
    )


def test_evaluation_cases_have_practical_review_criteria():
    cases = load_cases()
    assert len(cases) >= 30
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert len(case["must_identify"]) >= 3
        assert case["acceptable_hexagrams"]
