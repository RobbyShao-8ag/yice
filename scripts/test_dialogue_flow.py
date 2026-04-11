#!/usr/bin/env python3
"""
End-to-end test for dialogue flow with context coherence.

测试场景专属问题和上下文连贯性。

运行方式：
    python scripts/test_dialogue_flow.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
from agents.question_analyzer import QuestionAnalyzer


def create_mock_llm_call(scenario_type: str):
    """创建模拟 LLM 调用，根据场景类型返回预定义响应"""

    # 场景专属的首问题响应
    first_question_responses = {
        "chuangye": {
            "question_type": "创业",
            "domain": "创业投资",
            "required_info": ["project_type", "capital_status", "team_status"],
            "first_question": {
                "text": "您打算在哪个领域创业？",
                "options": [
                    "A. 科技/互联网",
                    "B. 实体店铺",
                    "C. 服务行业",
                    "D. 其他（请补充）",
                ],
                "field": "project_type",
            },
        },
        "shiye": {
            "question_type": "职场",
            "domain": "事业发展",
            "required_info": ["career_stage", "career_goal"],
            "first_question": {
                "text": "您目前的职业阶段是？",
                "options": [
                    "A. 刚入职场 (1-3 年)",
                    "B. 职业成长期 (3-5 年)",
                    "C. 职业成熟期 (5-10 年)",
                    "D. 其他（请补充）",
                ],
                "field": "career_stage",
            },
        },
        "ganqing": {
            "question_type": "感情",
            "domain": "感情婚姻",
            "required_info": ["relationship_status", "relationship_goal"],
            "first_question": {
                "text": "您目前的感情状态是？",
                "options": ["A. 单身", "B. 恋爱中", "C. 已婚", "D. 其他（请补充）"],
                "field": "relationship_status",
            },
        },
    }

    # 下一问题响应
    next_question_responses = {
        "chuangye": {
            "question": "您的资金状况如何？",
            "options": [
                "A. 自有资金充足",
                "B. 需要融资",
                "C. 资金紧张",
                "D. 其他（请补充）",
            ],
        },
        "shiye": {
            "question": "您希望实现什么职业目标？",
            "options": [
                "A. 晋升加薪",
                "B. 转行跳槽",
                "C. 创业准备",
                "D. 其他（请补充）",
            ],
        },
        "ganqing": {
            "question": "您希望达成什么感情目标？",
            "options": [
                "A. 找到合适伴侣",
                "B. 改善现有关系",
                "C. 婚姻决策",
                "D. 其他（请补充）",
            ],
        },
    }

    def mock_llm_call(system_prompt: str, user_prompt: str) -> str:
        # 判断是首问题还是下一问题
        if "参考场景信息" in user_prompt or "第一个问题" in user_prompt:
            # 首问题
            return json.dumps(
                first_question_responses[scenario_type], ensure_ascii=False
            )
        else:
            # 下一问题
            return json.dumps(
                next_question_responses[scenario_type], ensure_ascii=False
            )

    return mock_llm_call


def test_chuangye_scenario():
    """测试创业场景首问题精准"""
    print("\n" + "=" * 60)
    print("测试 1: 创业场景首问题精准")
    print("=" * 60)

    mock_call = create_mock_llm_call("chuangye")
    analyzer = QuestionAnalyzer(mock_call)

    analysis, first_question = analyzer.analyze(
        "我想问创业投资",
        scenario_hints={
            "question_type": "创业",
            "required_fields": ["project_type", "capital_status", "team_status"],
        },
    )

    # 验证问题类型
    assert analysis.question_type == "创业", (
        f"期望问题类型为'创业'，实际：{analysis.question_type}"
    )

    # 验证首问题包含创业关键词
    question_text = first_question.question_text
    assert (
        "创业" in question_text or "领域" in question_text or "项目" in question_text
    ), f"首问题 '{question_text}' 应该包含创业相关关键词"

    # 验证 field 正确
    assert first_question.field == "project_type", (
        f"期望 field 为 'project_type'，实际：{first_question.field}"
    )

    # 验证选项
    assert len(first_question.options) == 4, (
        f"期望 4 个选项，实际：{len(first_question.options)}"
    )

    print(f"✅ 问题类型：{analysis.question_type}")
    print(f"✅ 首问题：{question_text}")
    print(f"✅ 收集字段：{first_question.field}")
    print(f"✅ 选项数：{len(first_question.options)}")
    print("✅ 创业场景测试通过！")


def test_shiye_scenario():
    """测试事业场景首问题精准"""
    print("\n" + "=" * 60)
    print("测试 2: 事业场景首问题精准")
    print("=" * 60)

    mock_call = create_mock_llm_call("shiye")
    analyzer = QuestionAnalyzer(mock_call)

    analysis, first_question = analyzer.analyze(
        "我想问事业发展",
        scenario_hints={
            "question_type": "职场",
            "required_fields": ["career_stage", "career_goal"],
        },
    )

    # 验证问题类型
    assert analysis.question_type == "职场", (
        f"期望问题类型为'职场'，实际：{analysis.question_type}"
    )

    # 验证首问题包含事业关键词
    question_text = first_question.question_text
    assert (
        "职业" in question_text or "事业" in question_text or "阶段" in question_text
    ), f"首问题 '{question_text}' 应该包含事业相关关键词"

    # 验证 field 正确
    assert first_question.field == "career_stage", (
        f"期望 field 为 'career_stage'，实际：{first_question.field}"
    )

    print(f"✅ 问题类型：{analysis.question_type}")
    print(f"✅ 首问题：{question_text}")
    print(f"✅ 收集字段：{first_question.field}")
    print("✅ 事业场景测试通过！")


def test_ganqing_scenario():
    """测试感情场景首问题精准"""
    print("\n" + "=" * 60)
    print("测试 3: 感情场景首问题精准")
    print("=" * 60)

    mock_call = create_mock_llm_call("ganqing")
    analyzer = QuestionAnalyzer(mock_call)

    analysis, first_question = analyzer.analyze(
        "我想问感情婚姻",
        scenario_hints={
            "question_type": "感情",
            "required_fields": ["relationship_status", "relationship_goal"],
        },
    )

    # 验证问题类型
    assert analysis.question_type == "感情", (
        f"期望问题类型为'感情'，实际：{analysis.question_type}"
    )

    # 验证首问题包含感情关键词
    question_text = first_question.question_text
    assert (
        "感情" in question_text or "状态" in question_text or "恋爱" in question_text
    ), f"首问题 '{question_text}' 应该包含感情相关关键词"

    # 验证 field 正确
    assert first_question.field == "relationship_status", (
        f"期望 field 为 'relationship_status'，实际：{first_question.field}"
    )

    print(f"✅ 问题类型：{analysis.question_type}")
    print(f"✅ 首问题：{question_text}")
    print(f"✅ 收集字段：{first_question.field}")
    print("✅ 感情场景测试通过！")


def test_context_coherence():
    """测试上下文连贯性：下一问题基于用户回答生成"""
    print("\n" + "=" * 60)
    print("测试 4: 上下文连贯性")
    print("=" * 60)

    from agents.qigua_agent import QiguaAgent

    # 模拟 LLM 调用
    call_count = [0]

    def mock_llm_call(system_prompt: str, user_prompt: str) -> str:
        call_count[0] += 1

        # 第一次调用：生成首问题
        if call_count[0] == 1:
            return json.dumps(
                {
                    "question_type": "创业",
                    "domain": "创业投资",
                    "required_info": ["project_type"],
                    "first_question": {
                        "text": "您打算在哪个领域创业？",
                        "options": [
                            "A. 科技/互联网",
                            "B. 实体店铺",
                            "C. 服务行业",
                            "D. 其他（请补充）",
                        ],
                        "field": "project_type",
                    },
                },
                ensure_ascii=False,
            )
        # 第二次调用：充分性检查（返回不充分）
        elif call_count[0] == 2:
            return json.dumps(
                {
                    "is_sufficient": False,
                    "missing_info": ["还需要了解资金状况"],
                    "reasoning": "信息不足",
                },
                ensure_ascii=False,
            )
        # 第三次调用：生成下一问题
        else:
            # 验证 prompt 中包含用户上一轮回答
            assert "科技/互联网" in user_prompt, (
                f"Prompt 应该包含用户回答 '科技/互联网'，实际：{user_prompt[:200]}"
            )

            return json.dumps(
                {
                    "question": "您的资金状况如何？",
                    "options": [
                        "A. 自有资金充足",
                        "B. 需要融资",
                        "C. 资金紧张",
                        "D. 其他（请补充）",
                    ],
                },
                ensure_ascii=False,
            )

    # 创建 Agent（不执行完整流程，只测试 prompt 构建）
    agent = QiguaAgent(QiguaAgentConfig(llm_call=mock_llm_call, max_rounds=2))

    # 测试 _build_next_question_prompt 方法
    dialogue_history = [
        {
            "round": 1,
            "question": "您打算在哪个领域创业？",
            "options": [
                "A. 科技/互联网",
                "B. 实体店铺",
                "C. 服务行业",
                "D. 其他（请补充）",
            ],
            "answer": "A",
            "answer_text": "科技/互联网",
            "field": "project_type",
        }
    ]
    extra_context = {"project_type": "科技/互联网"}

    # 验证 prompt 包含用户回答
    prompt = agent._build_next_question_prompt("创业", extra_context, dialogue_history)

    assert "科技/互联网" in prompt, f"Prompt 应该包含用户回答 '科技/互联网'"
    assert "用户刚才回答了" in prompt, f"Prompt 应该包含上下文连贯性指示"
    assert "基于用户的回答" in prompt or "相关" in prompt, (
        f"Prompt 应该强调基于用户回答生成问题"
    )

    print(f"✅ 对话历史：{len(dialogue_history)} 轮")
    print(f"✅ 用户回答：{dialogue_history[0]['answer_text']}")
    print(f"✅ Prompt 包含用户回答：✓")
    print(f"✅ Prompt 包含连贯性指示：✓")
    print("✅ 上下文连贯性测试通过！")


def test_scenario_questions_data():
    """测试场景问题模板数据完整性"""
    print("\n" + "=" * 60)
    print("测试 5: 场景问题模板数据")
    print("=" * 60)

    from pathlib import Path

    data_file = PROJECT_ROOT / "data" / "scenario_questions.json"
    assert data_file.exists(), f"场景问题模板文件不存在：{data_file}"

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 验证核心场景
    expected_scenarios = {"chuangye", "shiye", "ganqing", "touzi"}
    actual_scenarios = set(data.keys())
    assert expected_scenarios.issubset(actual_scenarios), (
        f"缺少核心场景：{expected_scenarios - actual_scenarios}"
    )

    # 验证每个场景的问题数量
    for scenario_key, scenario_data in data.items():
        questions = scenario_data.get("questions", [])
        assert len(questions) >= 3, (
            f"场景 {scenario_key} 至少有 3 个问题，实际：{len(questions)}"
        )

        # 验证问题结构
        for idx, question in enumerate(questions):
            assert "field" in question, (
                f"场景 {scenario_key} 的第 {idx + 1} 个问题缺少 field"
            )
            assert "question" in question, (
                f"场景 {scenario_key} 的第 {idx + 1} 个问题缺少 question"
            )
            assert "options" in question, (
                f"场景 {scenario_key} 的第 {idx + 1} 个问题缺少 options"
            )
            assert len(question["options"]) == 4, (
                f"场景 {scenario_key} 的第 {idx + 1} 个问题应该有 4 个选项"
            )

    print(f"✅ 核心场景数：{len(expected_scenarios)}")
    print(f"✅ 所有场景问题数 >= 3")
    print(f"✅ 所有问题结构完整")
    print("✅ 场景问题模板数据测试通过！")


def test_scene_mapping_reference():
    """测试场景映射引用正确"""
    print("\n" + "=" * 60)
    print("测试 6: 场景映射引用")
    print("=" * 60)

    from pathlib import Path

    mapping_file = PROJECT_ROOT / "data" / "scene_mapping.json"
    questions_file = PROJECT_ROOT / "data" / "scenario_questions.json"

    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # 验证 scenario_key 引用
    scenarios_with_key = [
        (k, v["scenario_key"]) for k, v in mapping.items() if "scenario_key" in v
    ]

    assert len(scenarios_with_key) >= 5, (
        f"至少有 5 个场景包含 scenario_key，实际：{len(scenarios_with_key)}"
    )

    # 验证所有 scenario_key 都能在 questions 中找到
    valid_keys = set(questions.keys())
    for scene_key, scenario_key in scenarios_with_key:
        assert scenario_key in valid_keys, (
            f"场景 {scene_key} 的 scenario_key '{scenario_key}' 在 questions 中不存在"
        )

    print(f"✅ 有 scenario_key 的场景数：{len(scenarios_with_key)}")
    print(f"✅ 所有 scenario_key 引用有效")
    print("✅ 场景映射引用测试通过！")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("易策对话流程端到端测试")
    print("=" * 60)

    try:
        test_chuangye_scenario()
        test_shiye_scenario()
        test_ganqing_scenario()
        test_context_coherence()
        test_scenario_questions_data()
        test_scene_mapping_reference()

        print("\n" + "=" * 60)
        print("✅✅✅ 所有端到端测试通过！✅✅✅")
        print("=" * 60)
        print("\n测试覆盖:")
        print("  1. 创业场景首问题精准 ✓")
        print("  2. 事业场景首问题精准 ✓")
        print("  3. 感情场景首问题精准 ✓")
        print("  4. 上下文连贯性 ✓")
        print("  5. 场景问题模板数据 ✓")
        print("  6. 场景映射引用 ✓")
        print()

    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常：{e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
