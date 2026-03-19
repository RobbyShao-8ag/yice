"""
Tests for scenario-specific question templates.

测试场景专属问题模板的加载和匹配功能。
"""

import json
import pytest
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@pytest.fixture
def scenario_questions():
    """加载场景问题模板数据"""
    with open(DATA_DIR / "scenario_questions.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def scene_mapping():
    """加载场景映射数据"""
    with open(DATA_DIR / "scene_mapping.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestScenarioQuestions:
    """场景问题模板测试"""

    def test_scenario_questions_load(self, scenario_questions):
        """测试场景问题模板可以正确加载"""
        assert scenario_questions is not None
        assert isinstance(scenario_questions, dict)

    def test_scenario_count(self, scenario_questions):
        """测试包含 4 个核心场景"""
        expected_scenarios = {"chuangye", "shiye", "ganqing", "touzi"}
        actual_scenarios = set(scenario_questions.keys())

        assert expected_scenarios.issubset(actual_scenarios), (
            f"缺少核心场景：{expected_scenarios - actual_scenarios}"
        )

    def test_scenario_structure(self, scenario_questions):
        """测试每个场景的结构完整"""
        required_fields = {"scenario_name", "question_type", "questions"}

        for scenario_key, scenario_data in scenario_questions.items():
            for field in required_fields:
                assert field in scenario_data, (
                    f"场景 {scenario_key} 缺少必需字段：{field}"
                )

            assert isinstance(scenario_data["questions"], list), (
                f"场景 {scenario_key} 的 questions 必须是列表"
            )

    def test_question_structure(self, scenario_questions):
        """测试每个问题的字段完整"""
        required_fields = {"order", "field", "question", "options"}

        for scenario_key, scenario_data in scenario_questions.items():
            for idx, question in enumerate(scenario_data["questions"]):
                for field in required_fields:
                    assert field in question, (
                        f"场景 {scenario_key} 的第 {idx + 1} 个问题缺少字段：{field}"
                    )

                # 验证字段类型
                assert isinstance(question["order"], int), (
                    f"场景 {scenario_key} 的问题 order 必须是整数"
                )
                assert isinstance(question["field"], str), (
                    f"场景 {scenario_key} 的问题 field 必须是字符串"
                )
                assert isinstance(question["question"], str), (
                    f"场景 {scenario_key} 的问题 question 必须是字符串"
                )
                assert isinstance(question["options"], list), (
                    f"场景 {scenario_key} 的问题 options 必须是列表"
                )

    def test_scenario_question_count(self, scenario_questions):
        """测试每个场景至少有 3 个问题"""
        for scenario_key, scenario_data in scenario_questions.items():
            question_count = len(scenario_data["questions"])
            assert question_count >= 3, (
                f"场景 {scenario_key} 至少有 3 个问题，当前：{question_count}"
            )

    def test_options_count(self, scenario_questions):
        """测试每个问题有 4 个选项"""
        for scenario_key, scenario_data in scenario_questions.items():
            for idx, question in enumerate(scenario_data["questions"]):
                option_count = len(question["options"])
                assert option_count == 4, (
                    f"场景 {scenario_key} 的第 {idx + 1} 个问题应该有 4 个选项，当前：{option_count}"
                )

    def test_field_naming_convention(self, scenario_questions):
        """测试 field 使用英文 snake_case 命名"""
        import re

        snake_case_pattern = re.compile(r"^[a-z]+(_[a-z]+)*$")

        for scenario_key, scenario_data in scenario_questions.items():
            for idx, question in enumerate(scenario_data["questions"]):
                field = question["field"]
                assert snake_case_pattern.match(field), (
                    f"场景 {scenario_key} 的第 {idx + 1} 个问题的 field '{field}' 不符合 snake_case 命名规范"
                )

    def test_last_option_is_other(self, scenario_questions):
        """测试每个问题的最后一个选项是"其他（请补充）"""
        for scenario_key, scenario_data in scenario_questions.items():
            for idx, question in enumerate(scenario_data["questions"]):
                last_option = question["options"][-1]
                assert "其他" in last_option and "补充" in last_option, (
                    f"场景 {scenario_key} 的第 {idx + 1} 个问题的最后一个选项应该是'其他（请补充）'，当前：{last_option}"
                )


class TestSceneMappingReference:
    """场景映射引用测试"""

    def test_scene_mapping_load(self, scene_mapping):
        """测试场景映射可以正确加载"""
        assert scene_mapping is not None
        assert isinstance(scene_mapping, dict)

    def test_scenario_key_reference(self, scene_mapping, scenario_questions):
        """测试 scene_mapping.json 中的 scenario_key 引用正确"""
        # 应该有 5 个场景包含 scenario_key
        scenarios_with_key = [
            (k, v["scenario_key"])
            for k, v in scene_mapping.items()
            if "scenario_key" in v
        ]

        assert len(scenarios_with_key) == 5, (
            f"应该有 5 个场景包含 scenario_key，当前：{len(scenarios_with_key)}"
        )

        # 验证所有 scenario_key 都能在 scenario_questions.json 中找到
        valid_keys = set(scenario_questions.keys())
        for scene_key, scenario_key in scenarios_with_key:
            assert scenario_key in valid_keys, (
                f"场景 {scene_key} 的 scenario_key '{scenario_key}' 在 scenario_questions.json 中不存在"
            )

    def test_core_scenarios_have_reference(self, scene_mapping):
        """测试核心场景都有 scenario_key 引用"""
        # 动态查找核心场景（通过 keywords 匹配）
        core_scenario_keywords = {
            "创业": "chuangye",
            "职场": "shiye",
            "投资": "touzi",
        }

        # 特殊处理感情场景
        found_ganqing = False

        for scene_key, scene_data in scene_mapping.items():
            if "scenario_key" not in scene_data:
                continue

            keywords = scene_data.get("keywords", [])
            scenario_key = scene_data["scenario_key"]

            # 检查创业场景
            if scene_key.startswith("创业"):
                assert scenario_key == "chuangye", (
                    f"创业场景 {scene_key} 的 scenario_key 应该是 chuangye"
                )
            # 检查职场场景
            elif scene_key.startswith("职场"):
                assert scenario_key == "shiye", (
                    f"职场场景 {scene_key} 的 scenario_key 应该是 shiye"
                )
            # 检查投资场景
            elif scene_key.startswith("投资"):
                assert scenario_key == "touzi", (
                    f"投资场景 {scene_key} 的 scenario_key 应该是 touzi"
                )
            # 检查感情场景
            elif scene_key == "scenario_105":
                assert scenario_key == "ganqing", (
                    f"感情场景 scenario_105 的 scenario_key 应该是 ganqing"
                )
                found_ganqing = True

        assert found_ganqing, "感情场景 scenario_105 应该有 scenario_key"

    def test_hexagram_mapping_unchanged(self, scene_mapping):
        """测试添加 scenario_key 没有改变卦象映射"""
        # 验证包含 scenario_key 的场景的卦象映射
        expected_hexagrams = {
            "创业": {3, 1},  # 屯、乾
            "职场": {46},  # 升
            "投资": {40},  # 解
            "scenario_105": {6},  # 讼
        }

        for scene_key, scene_data in scene_mapping.items():
            if "scenario_key" not in scene_data:
                continue

            hexagram_id = scene_data["hexagram_id"]

            if scene_key.startswith("创业"):
                assert hexagram_id in expected_hexagrams["创业"], (
                    f"创业场景 {scene_key} 的 hexagram_id 应该是 3 或 1"
                )
            elif scene_key.startswith("职场"):
                assert hexagram_id == 46, (
                    f"职场场景 {scene_key} 的 hexagram_id 应该是 46"
                )
            elif scene_key.startswith("投资"):
                assert hexagram_id == 40, (
                    f"投资场景 {scene_key} 的 hexagram_id 应该是 40"
                )
            elif scene_key == "scenario_105":
                assert hexagram_id == 6, (
                    f"感情场景 scenario_105 的 hexagram_id 应该是 6"
                )


class TestIntegration:
    """集成测试"""

    def test_scenario_questions_json_format(self):
        """测试 scenario_questions.json 格式正确"""
        json_file = DATA_DIR / "scenario_questions.json"

        # 应该可以解析
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 验证是有效的 JSON 对象
        assert isinstance(data, dict)

        # 验证没有语法错误（重新序列化再解析）
        json_str = json.dumps(data, ensure_ascii=False)
        reparsed = json.loads(json_str)
        assert reparsed == data, "JSON 序列化/反序列化后数据不一致"

    def test_scene_mapping_json_format(self):
        """测试 scene_mapping.json 格式正确"""
        json_file = DATA_DIR / "scene_mapping.json"

        # 应该可以解析
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 验证是有效的 JSON 对象
        assert isinstance(data, dict)

        # 验证没有语法错误（重新序列化再解析）
        json_str = json.dumps(data, ensure_ascii=False)
        reparsed = json.loads(json_str)
        assert reparsed == data, "JSON 序列化/反序列化后数据不一致"
