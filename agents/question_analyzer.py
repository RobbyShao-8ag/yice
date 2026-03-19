"""
LLM-driven question analyzer for the yice decision system.

问题分析器 - 通过 LLM 动态识别问题类型、需要收集的信息、生成对话问题。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class QuestionAnalysis:
    """问题分类结果"""

    question_type: str  # 动态识别的类型（如：个人发展、职业选择、生活决策等）
    domain: str  # 具体领域（如：音乐、投资、职业等）
    required_info: list[str] = field(default_factory=list)  # 需要收集的信息
    irrelevant_info: list[str] = field(default_factory=list)  # 不需要的信息


@dataclass
class DialogueQuestion:
    """对话问题"""

    question_text: str  # 问题内容
    options: list[str] = field(default_factory=list)  # 3-4 个选项
    field: str = ""  # 对应 QuestionContext.extra_context 的字段名


class QuestionAnalyzerError(Exception):
    """Base exception for QuestionAnalyzer errors."""

    pass


class LLMCallError(QuestionAnalyzerError):
    """LLM call failed."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class JSONParseError(QuestionAnalyzerError):
    """Failed to parse LLM response as JSON."""

    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


class QuestionAnalyzer:
    """LLM 问题分析器

    通过 LLM 动态分析用户问题，识别：
    - 问题类型和领域
    - 需要收集的关键信息
    - 生成第一个对话问题（含选项）
    """

    SYSTEM_PROMPT = "你是易经占卜系统的起卦官，擅长分析用户问题并提供针对性的决策建议。"

    def __init__(self, llm_call: Callable[[str, str], str]):
        """初始化分析器

        Args:
            llm_call: LLM 调用回调函数，接收 (system_prompt, user_prompt)，返回响应文本
        """
        self.llm_call = llm_call

    def analyze(
        self, raw_question: str, scenario_hints: Optional[dict] = None
    ) -> tuple[QuestionAnalysis, DialogueQuestion]:
        """分析用户问题，返回类型识别和第一个问题

        Args:
            raw_question: 用户原始问题
            scenario_hints: 可选的场景提示，包含 question_type 和 required_fields

        Returns:
            tuple[QuestionAnalysis, DialogueQuestion]: 问题分类结果 + 第一个问题

        Raises:
            LLMCallError: LLM 调用失败
            JSONParseError: JSON 解析失败
        """
        prompt = self._build_analysis_prompt(raw_question, scenario_hints)

        try:
            response = self.llm_call(self.SYSTEM_PROMPT, prompt)
        except Exception as e:
            raise LLMCallError(f"LLM 调用失败：{e}", cause=e)

        return self._parse_response(response)

    def _build_analysis_prompt(
        self, question: str, scenario_hints: Optional[dict] = None
    ) -> str:
        """构建分析提示词

        Args:
            question: 用户原始问题
            scenario_hints: 可选的场景提示，包含 question_type 和 required_fields

        Returns:
            构建好的提示词
        """
        hints_text = ""
        if scenario_hints:
            required_fields = scenario_hints.get("required_fields", [])
            fields_str = ", ".join(required_fields) if required_fields else "待分析"
            hints_text = f"""
参考场景信息：
- 场景类型：{scenario_hints.get('question_type', '综合')}
- 建议收集：{fields_str}
"""

        return f"""用户问题：{question}
{hints_text}
请分析：
1. 这是什么类型的问题？（例如：职业发展、个人兴趣、生活决策等）
2. 为了给用户好的六爻占卜建议，需要收集哪些关键信息？
3. 第一个问题应该问什么？请提供 3-4 个选项。

返回 JSON 格式（只返回 JSON，不要其他文字）：
{{
    "question_type": "类型",
    "domain": "具体领域",
    "required_info": ["信息 1", "信息 2", ...],
    "irrelevant_info": ["不需要的信息 1", ...],
    "first_question": {{
        "text": "问题内容",
        "options": ["A. 选项 1", "B. 选项 2", "C. 选项 3", "D. 其他（请补充）"],
        "field": "extra_context 的字段名（使用英文 snake_case）"
    }}
}}"""

    def _parse_response(
        self, response: str
    ) -> tuple[QuestionAnalysis, DialogueQuestion]:
        """解析 LLM 响应

        Args:
            response: LLM 原始响应文本

        Returns:
            tuple[QuestionAnalysis, DialogueQuestion]: 解析后的数据对象

        Raises:
            JSONParseError: JSON 解析失败或数据验证失败
        """
        # 尝试提取 JSON 块
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise JSONParseError(
                f"无法解析 LLM 响应为 JSON: {e}\n原始响应：{response[:200]}...",
                raw_response=response,
            )

        # 验证必需字段
        required_fields = ["question_type", "domain", "first_question"]
        for field in required_fields:
            if field not in data:
                raise JSONParseError(
                    f"LLM 响应缺少必需字段：{field}\n原始响应：{response[:200]}...",
                    raw_response=response,
                )

        # 构建 QuestionAnalysis
        analysis = QuestionAnalysis(
            question_type=data.get("question_type", "综合决策"),
            domain=data.get("domain", ""),
            required_info=data.get("required_info", []),
            irrelevant_info=data.get("irrelevant_info", []),
        )

        # 构建 DialogueQuestion
        first_q = data.get("first_question", {})
        question = DialogueQuestion(
            question_text=first_q.get("text", ""),
            options=first_q.get("options", []),
            field=first_q.get("field", ""),
        )

        # 验证 DialogueQuestion
        if not question.question_text:
            raise JSONParseError(
                f"第一个问题缺少问题内容\n原始响应：{response[:200]}...",
                raw_response=response,
            )

        # 确保有选项（如果没有，添加默认的"其他"选项）
        if not question.options:
            question.options = ["A. 是", "B. 否", "C. 不确定", "D. 其他（请补充）"]

        return analysis, question

    def _extract_json(self, response: str) -> str:
        """从响应中提取 JSON 块

        处理 LLM 可能在 JSON 前后添加其他文字的情况。

        Args:
            response: LLM 原始响应

        Returns:
            提取出的 JSON 字符串
        """
        response = response.strip()

        # 如果整个响应就是 JSON 对象
        if response.startswith("{") and response.endswith("}"):
            return response

        # 尝试提取 ```json ... ``` 代码块
        json_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL
        )
        if json_block_match:
            return json_block_match.group(1).strip()

        # 尝试找到第一个 { 和最后一个 }
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            return response[start : end + 1]

        # 无法提取，返回原始响应
        return response
