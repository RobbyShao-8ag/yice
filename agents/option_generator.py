"""
OptionGenerator for the yice decision system.

动态选项生成器 - 通过 LLM 动态生成对话选项。
"""

import json
import re
from dataclasses import dataclass
from typing import Callable

from core.models import QuestionContext


@dataclass
class GeneratedOption:
    """生成的选项"""

    text: str
    label: str  # A, B, C, D


class OptionGeneratorError(Exception):
    """Base exception for OptionGenerator errors."""

    pass


class OptionGenerator:
    """LLM 驱动的动态选项生成器

    根据当前问题上下文，动态生成 3-4 个选项供用户选择。
    最后一个选项总是 "D. 其他（请补充）"。
    """

    SYSTEM_PROMPT = (
        "你是易经占卜系统的对话选项生成专家，擅长生成符合用户问题语境的选项。"
    )

    def __init__(self, llm_call: Callable[[str, str], str]):
        """初始化生成器

        Args:
            llm_call: LLM 调用回调函数
        """
        self.llm_call = llm_call

    def generate(
        self,
        question_type: str,
        question_text: str,
        context: dict,
    ) -> list[str]:
        """生成对话选项

        Args:
            question_type: 问题类型
            question_text: 问题文本
            context: 额外的上下文信息

        Returns:
            list[str]: 选项列表，如 ["A. 选项1", "B. 选项2", ...]
        """
        prompt = self._build_prompt(question_type, question_text, context)

        try:
            response = self.llm_call(self.SYSTEM_PROMPT, prompt)
        except Exception as e:
            return self._fallback_options()

        return self._parse_response(response)

    def _build_prompt(
        self, question_type: str, question_text: str, context: dict
    ) -> str:
        """构建选项生成提示词

        Args:
            question_type: 问题类型
            question_text: 问题文本
            context: 上下文信息

        Returns:
            提示词
        """
        # 构建上下文摘要
        context_parts = []
        for key, value in context.items():
            if value:
                context_parts.append(f"{key}: {value}")

        context_text = "\n".join(context_parts) if context_parts else "（暂无）"

        return f"""问题类型: {question_type}
问题: {question_text}

已收集的信息:
{context_text}

请为上述问题生成 3-4 个选项。选项应该：
1. 覆盖常见的用户情境
2. 简洁明了，便于用户理解
3. 最后一个选项必须是 "D. 其他（请补充）"

返回 JSON 格式（只返回JSON，不要其他文字）：
{{
    "options": [
        "A. 选项1",
        "B. 选项2", 
        "C. 选项3",
        "D. 其他（请补充）"
    ]
}}"""

    def _parse_response(self, response: str) -> list[str]:
        """解析 LLM 响应

        Args:
            response: LLM 原始响应

        Returns:
            list[str]: 选项列表
        """
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
            options = data.get("options", [])
            if options and isinstance(options, list):
                # 确保最后一个是 "其他"
                if not any("其他" in opt for opt in options):
                    options.append("D. 其他（请补充）")
                return options
        except json.JSONDecodeError:
            pass

        return self._fallback_options()

    def _fallback_options(self) -> list[str]:
        """返回默认选项

        Returns:
            list[str]: 默认选项列表
        """
        return [
            "A. 是的，完全符合",
            "B. 部分符合",
            "C. 不太符合",
            "D. 其他（请补充）",
        ]

    def _extract_json(self, response: str) -> str:
        """从响应中提取 JSON 块

        Args:
            response: LLM 原始响应

        Returns:
            提取出的 JSON 字符串
        """
        response = response.strip()

        if response.startswith("{") and response.endswith("}"):
            return response

        json_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL
        )
        if json_block_match:
            return json_block_match.group(1).strip()

        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            return response[start : end + 1]

        return response
