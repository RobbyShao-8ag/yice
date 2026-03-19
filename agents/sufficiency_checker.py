"""
SufficiencyChecker for the yice decision system.

信息充分性检查器 - 通过 LLM 判断当前收集的信息是否足够进行六爻占卜。
"""

import json
import re
from dataclasses import dataclass
from typing import Callable

from core.models import QuestionContext


@dataclass
class SufficiencyResult:
    """信息充分性检查结果"""

    is_sufficient: bool
    missing_info: list[str]
    reasoning: str
    next_question: str | None = None


class SufficiencyCheckerError(Exception):
    """Base exception for SufficiencyChecker errors."""

    pass


class SufficiencyChecker:
    """LLM 驱动的信息充分性检查器

    在每轮对话后检查收集的信息是否足够：
    - 如果足够，返回 is_sufficient=True
    - 如果不足，返回缺失的信息列表和建议的下一个问题
    """

    SYSTEM_PROMPT = "你是易经占卜系统的问题充分性分析专家，擅长判断用户是否提供了足够的信息来进行有意义的占卜分析。"

    def __init__(self, llm_call: Callable[[str, str], str]):
        """初始化检查器

        Args:
            llm_call: LLM 调用回调函数
        """
        self.llm_call = llm_call

    def check(self, ctx: QuestionContext) -> SufficiencyResult:
        """检查收集的信息是否足够

        Args:
            ctx: 当前的问题上下文

        Returns:
            SufficiencyResult: 检查结果
        """
        # 如果对话历史为空，说明刚开始检查
        if not ctx.dialogue_history:
            return SufficiencyResult(
                is_sufficient=False,
                missing_info=["背景信息", "约束条件", "期望目标"],
                reasoning="刚开始收集信息，需要更多背景",
                next_question="请描述您当前面临的具体情况",
            )

        prompt = self._build_check_prompt(ctx)

        try:
            response = self.llm_call(self.SYSTEM_PROMPT, prompt)
        except Exception as e:
            # LLM 调用失败，默认认为信息不足
            return SufficiencyResult(
                is_sufficient=False,
                missing_info=["无法确定"],
                reasoning=f"LLM调用失败: {e}",
            )

        return self._parse_response(response)

    def _build_check_prompt(self, ctx: QuestionContext) -> str:
        """构建检查提示词

        Args:
            ctx: 问题上下文

        Returns:
            提示词
        """
        # 收集已有的信息摘要
        info_summary = []
        info_summary.append(f"原始问题: {ctx.raw_question}")
        info_summary.append(f"问题类型: {ctx.question_type}")

        for entry in ctx.dialogue_history:
            field = entry.get("field", "未知")
            answer = entry.get("answer_text", "")
            info_summary.append(f"{field}: {answer}")

        info_text = "\n".join(info_summary)

        return f"""当前收集的信息：
{info_text}

请判断以上信息是否足够进行六爻占卜分析。
考虑因素：
1. 是否有清晰的背景描述？
2. 是否有明确的约束条件？
3. 是否有具体的期望目标？
4. 是否包含时间范围和风险偏好？

返回 JSON 格式（只返回JSON，不要其他文字）：
{{
    "is_sufficient": true/false,
    "missing_info": ["缺失的信息1", "缺失的信息2", ...],
    "reasoning": "判断理由",
    "next_question": "如果不足，应该问什么问题？（仅在 is_sufficient=false 时需要）"
}}"""

    def _parse_response(self, response: str) -> SufficiencyResult:
        """解析 LLM 响应

        Args:
            response: LLM 原始响应

        Returns:
            SufficiencyResult: 解析后的结果
        """
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # JSON 解析失败，默认认为信息不足
            return SufficiencyResult(
                is_sufficient=False,
                missing_info=["无法解析LLM响应"],
                reasoning="JSON解析失败",
            )

        is_sufficient = data.get("is_sufficient", False)
        missing_info = data.get("missing_info", [])
        reasoning = data.get("reasoning", "")
        next_question = data.get("next_question")

        return SufficiencyResult(
            is_sufficient=is_sufficient,
            missing_info=missing_info if isinstance(missing_info, list) else [],
            reasoning=reasoning,
            next_question=next_question if is_sufficient else None,
        )

    def _extract_json(self, response: str) -> str:
        """从响应中提取 JSON 块

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

        return response
