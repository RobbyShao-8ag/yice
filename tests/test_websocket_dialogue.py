"""
Tests for WebSocket dialogue history storage and extra_context synchronization.

测试 WebSocket 对话历史完整存储和 extra_context 同步更新功能。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestParseAnswer:
    """parse_answer 函数测试"""

    def test_parse_answer_letter_a(self):
        """测试字母选项解析 A"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert parse_answer("A", options) == "科技/互联网"
        assert parse_answer("a", options) == "科技/互联网"

    def test_parse_answer_letter_b(self):
        """测试字母选项解析 B"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert parse_answer("B", options) == "实体店铺"
        assert parse_answer("b", options) == "实体店铺"

    def test_parse_answer_letter_c(self):
        """测试字母选项解析 C"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert parse_answer("C", options) == "服务行业"
        assert parse_answer("c", options) == "服务行业"

    def test_parse_answer_letter_d(self):
        """测试字母选项解析 D"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert parse_answer("D", options) == "其他（请补充）"
        assert parse_answer("d", options) == "其他（请补充）"

    def test_parse_answer_number(self):
        """测试数字选项解析"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert parse_answer("1", options) == "科技/互联网"
        assert parse_answer("2", options) == "实体店铺"
        assert parse_answer("3", options) == "服务行业"
        assert parse_answer("4", options) == "其他（请补充）"

    def test_parse_answer_text_direct_match(self):
        """测试直接文本匹配"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert parse_answer("科技/互联网", options) == "科技/互联网"
        assert parse_answer("实体店铺", options) == "实体店铺"

    def test_parse_answer_no_options(self):
        """测试没有选项时返回原始答案"""
        from web.backend.routes.websocket import parse_answer

        assert parse_answer("自由文本", []) == "自由文本"
        assert parse_answer("测试", None) == "测试"

    def test_parse_answer_no_match(self):
        """测试无匹配时返回原始答案"""
        from web.backend.routes.websocket import parse_answer

        options = ["A. 选项 1", "B. 选项 2", "C. 选项 3"]
        assert parse_answer("不相关的内容", options) == "不相关的内容"
        assert parse_answer("X", options) == "X"


class TestDialogueSession:
    """DialogueSession 数据类测试"""

    def test_session_has_last_question_fields(self):
        """测试 Session 包含 last_question、last_options、last_field"""
        from web.backend.routes.websocket import DialogueSession
        from unittest.mock import Mock

        websocket = Mock()
        session = DialogueSession(websocket=websocket)

        # 验证字段存在
        assert hasattr(session, "last_question")
        assert hasattr(session, "last_options")
        assert hasattr(session, "last_field")

        # 验证初始值
        assert session.last_question == ""
        assert session.last_options == []
        assert session.last_field == ""

    def test_session_last_fields_can_be_set(self):
        """测试 Session 的 last 字段可以被设置"""
        from web.backend.routes.websocket import DialogueSession
        from unittest.mock import Mock

        websocket = Mock()
        session = DialogueSession(websocket=websocket)

        # 设置值
        session.last_question = "您打算在哪个领域创业？"
        session.last_options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        session.last_field = "project_type"

        # 验证值
        assert session.last_question == "您打算在哪个领域创业？"
        assert session.last_options == ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        assert session.last_field == "project_type"


class TestDialogueHistory:
    """对话历史测试"""

    def test_dialogue_history_structure(self):
        """测试对话历史包含完整字段"""
        from web.backend.routes.websocket import DialogueSession
        from unittest.mock import Mock

        websocket = Mock()
        session = DialogueSession(websocket=websocket)

        # 模拟设置 last 字段（注意：选项包含前缀，因为 parse_answer 需要前缀来解析）
        session.last_question = "您打算在哪个领域创业？"
        session.last_options = [
            "A. 科技/互联网",
            "B. 实体店铺",
            "C. 服务行业",
            "D. 其他（请补充）",
        ]
        session.last_field = "project_type"

        # 模拟存储对话历史（导入 parse_answer）
        from web.backend.routes.websocket import parse_answer

        content = "A"
        answer_text = parse_answer(content, session.last_options)

        session.dialogue_history.append(
            {
                "round": session.current_round + 1,
                "question": session.last_question,
                "options": session.last_options,
                "answer": content,
                "answer_text": answer_text,
                "field": session.last_field,
            }
        )
        session.current_round += 1

        # 验证对话历史结构
        assert len(session.dialogue_history) == 1
        history_entry = session.dialogue_history[0]

        # 验证所有必需字段
        assert "round" in history_entry
        assert "question" in history_entry
        assert "options" in history_entry
        assert "answer" in history_entry
        assert "answer_text" in history_entry
        assert "field" in history_entry

        # 验证字段值
        assert history_entry["round"] == 1
        assert history_entry["question"] == "您打算在哪个领域创业？"
        assert history_entry["options"] == [
            "A. 科技/互联网",
            "B. 实体店铺",
            "C. 服务行业",
            "D. 其他（请补充）",
        ]
        assert history_entry["answer"] == "A"
        assert history_entry["answer_text"] == "科技/互联网"
        assert history_entry["field"] == "project_type"

    def test_extra_context_update(self):
        """测试 extra_context 同步更新"""
        from web.backend.routes.websocket import DialogueSession, parse_answer
        from unittest.mock import Mock

        websocket = Mock()
        session = DialogueSession(websocket=websocket)

        # 模拟设置 last 字段
        session.last_question = "您打算在哪个领域创业？"
        session.last_options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        session.last_field = "project_type"

        # 模拟用户回答
        content = "A"
        answer_text = parse_answer(content, session.last_options)

        # 更新 extra_context
        if session.last_field:
            session.extra_context[session.last_field] = answer_text

        # 验证 extra_context 正确更新
        assert "project_type" in session.extra_context
        assert session.extra_context["project_type"] == "科技/互联网"

    def test_multiple_rounds_extra_context_accumulation(self):
        """测试多轮对话 extra_context 累积"""
        from web.backend.routes.websocket import DialogueSession, parse_answer
        from unittest.mock import Mock

        websocket = Mock()
        session = DialogueSession(websocket=websocket)

        # 第一轮
        session.last_question = "您打算在哪个领域创业？"
        session.last_options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        session.last_field = "project_type"

        content = "A"
        answer_text = parse_answer(content, session.last_options)

        session.dialogue_history.append(
            {
                "round": session.current_round + 1,
                "question": session.last_question,
                "options": session.last_options,
                "answer": content,
                "answer_text": answer_text,
                "field": session.last_field,
            }
        )
        session.current_round += 1

        if session.last_field:
            session.extra_context[session.last_field] = answer_text

        # 第二轮
        session.last_question = "您的资金状况如何？"
        session.last_options = ["A. 自有资金充足", "B. 需要融资", "C. 资金紧张", "D. 其他（请补充）"]
        session.last_field = "capital_status"

        content = "B"
        answer_text = parse_answer(content, session.last_options)

        session.dialogue_history.append(
            {
                "round": session.current_round + 1,
                "question": session.last_question,
                "options": session.last_options,
                "answer": content,
                "answer_text": answer_text,
                "field": session.last_field,
            }
        )
        session.current_round += 1

        if session.last_field:
            session.extra_context[session.last_field] = answer_text

        # 验证对话历史
        assert len(session.dialogue_history) == 2

        # 验证 extra_context 累积
        assert len(session.extra_context) == 2
        assert session.extra_context["project_type"] == "科技/互联网"
        assert session.extra_context["capital_status"] == "需要融资"


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_websocket_dialogue_flow(self):
        """测试完整的 WebSocket 对话流程"""
        from web.backend.routes.websocket import DialogueSession, parse_answer
        from unittest.mock import Mock, AsyncMock

        websocket = Mock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()

        session = DialogueSession(websocket=websocket)

        # 模拟第一轮：用户提问
        session.raw_question = "我想问创业投资"

        # 模拟生成首问题
        first_q_text = "您打算在哪个领域创业？"
        first_options = ["A. 科技/互联网", "B. 实体店铺", "C. 服务行业", "D. 其他（请补充）"]
        first_field = "project_type"

        session.last_question = first_q_text
        session.last_options = first_options
        session.last_field = first_field

        # 模拟用户回答
        user_answer = "A"
        answer_text = parse_answer(user_answer, first_options)

        # 存储对话历史
        session.dialogue_history.append(
            {
                "round": session.current_round + 1,
                "question": session.last_question,
                "options": session.last_options,
                "answer": user_answer,
                "answer_text": answer_text,
                "field": session.last_field,
            }
        )
        session.current_round += 1

        # 更新 extra_context
        if session.last_field:
            session.extra_context[session.last_field] = answer_text

        # 验证
        assert session.current_round == 1
        assert len(session.dialogue_history) == 1
        assert session.extra_context["project_type"] == "科技/互联网"

        history_entry = session.dialogue_history[0]
        assert history_entry["question"] == first_q_text
        assert history_entry["answer_text"] == answer_text
        assert history_entry["field"] == first_field
