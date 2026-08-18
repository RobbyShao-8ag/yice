"""
YaoAgents for the yice decision system.

Six yao position agents that analyze hexagram lines with fused
traditional and modern role definitions. Each agent focuses on
a specific aspect of the decision process.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.errors import PartialFailureError
from core.llm_filters import filter_think_content
from core.models import HexagramContext, YaoAnalysis, YaoPosition


def _parse_llm_response(response: str) -> dict[str, str]:
    response = filter_think_content(response)

    sections = {"解读": "", "建议": "", "风险": ""}
    current_section = None
    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()
        if re.match(r"^[#*\-]*\s*解读[:：]?\s*", line):
            current_section = "解读"
            content = re.sub(r"^[#*\-]*\s*解读[:：]?\s*", "", line)
            if content:
                sections["解读"] = content
        elif re.match(r"^[#*\-]*\s*建议[:：]?\s*", line):
            current_section = "建议"
            content = re.sub(r"^[#*\-]*\s*建议[:：]?\s*", "", line)
            if content:
                sections["建议"] = content
        elif re.match(r"^[#*\-]*\s*风险[:：]?\s*", line):
            current_section = "风险"
            content = re.sub(r"^[#*\-]*\s*风险[:：]?\s*", "", line)
            if content:
                sections["风险"] = content
        elif current_section and line:
            sections[current_section] += "\n" + line

    return sections


def _brief_line_text(text: str, limit: int = 56) -> str:
    """Return a compact line excerpt for local deterministic analysis."""
    cleaned = text.split("【", 1)[0]
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > limit:
        return cleaned[:limit].rstrip() + "..."
    return cleaned


def build_system_prompt(position: YaoPosition) -> str:
    """Build system prompt for a YaoAgent with fused role definition.

    Args:
        position: YaoPosition enum value (1-6)

    Returns:
        System prompt string with traditional and modern role fusion.
    """
    return f"""你是第{position.name_cn}分析官，对应{position.role}。

传统含义：{position.traditional_meaning}
现代映射：{position.role}
融合角色：{position.fused_role} - {position.analysis_focus}

你的任务是根据卦象爻辞，结合用户的具体问题，从{position.fused_role}的角度进行分析。
分析要点：
1. 理解爻辞在当前情境下的含义
2. 结合{position.analysis_focus}给出具体建议
3. 指出潜在风险和注意事项

输出格式：
- 解读：爻辞在当前情境下的含义解读
- 建议：具体可行的行动建议
- 风险：需要注意的风险点"""


@dataclass
class YaoAgentConfig:
    """Configuration for a YaoAgent instance."""

    position: YaoPosition
    provider: str = "minimax"  # Independent provider for this yao position
    model: str = "MiniMax-M2.5"  # Independent model for this yao position
    llm_call: Optional[Callable[[str, str], str]] = None

    @classmethod
    def from_models_config(cls, config: dict, position: int) -> "YaoAgentConfig":
        """Create YaoAgentConfig from models.json config.

        Args:
            config: models.json content
            position: Yao position (1-6)

        Returns:
            YaoAgentConfig with provider/model from config
        """
        agents = config.get("agents", {})
        agent_key = f"yao_{position}"
        agent_cfg = agents.get(agent_key, {})

        return cls(
            position=YaoPosition(position),
            provider=agent_cfg.get("provider", "minimax"),
            model=agent_cfg.get("model", "MiniMax-M2.5"),
        )


class YaoAgent:
    """Agent for analyzing a single yao position.

    Each YaoAgent is responsible for one of the six positions,
    applying fused traditional and modern role definitions to
    interpret the hexagram line for the user's question.
    """

    def __init__(self, config: YaoAgentConfig):
        self.position = config.position
        self._llm_call = config.llm_call
        self._system_prompt = build_system_prompt(config.position)

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return self._system_prompt

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        """Analyze a single yao line for the given question context.

        Args:
            hexagram_context: Context from scene router with hexagram data.
            line_data: Line data containing yao_ci and related info.

        Returns:
            YaoAnalysis with interpretation, advice, and risks.

        Raises:
            ValueError: If line_data is missing required fields.
        """
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]
        plain_explanation = line_data.get("plain_explanation", "")

        if self._llm_call is None:
            return self._generate_local_analysis(
                hexagram_context, line_name, yao_ci, plain_explanation
            )

        user_prompt = self._build_user_prompt(
            hexagram_context, line_name, yao_ci, plain_explanation
        )
        response = self._llm_call(self._system_prompt, user_prompt)

        return self._parse_response(self.position.value, line_name, yao_ci, response)

    def _build_user_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
        plain_explanation: str = "",
    ) -> str:
        """Build user prompt for LLM call."""
        question = hexagram_context.question
        return f"""用户问题：{question.raw_question}
问题类型：{question.question_type}
背景：{question.background}
约束：{question.constraints}
期望结果：{question.expected_outcome}
时间范围：{question.time_horizon}
风险承受：{question.risk_tolerance}

卦象：{hexagram_context.hexagram_name}（第{hexagram_context.hexagram_id}卦）
爻位：{line_name}
爻辞：{yao_ci}
经审核的白话提示：{plain_explanation or '暂无；请只依据原文和用户事实分析'}

请从{self.position.fused_role}的角度分析此爻辞对用户问题的启示。"""

    def _parse_response(
        self,
        position: int,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)
        analysis = sections["解读"].strip()
        advice = sections["建议"].strip()
        risks = sections["风险"].strip()

        if not analysis and not advice and not risks:
            analysis = "模型回复未按结构化格式返回，已保留爻位与爻辞供综合报告参考。"
            advice = "建议结合当前问题重新评估行动方案。"
            risks = "需警惕模型回复格式异常带来的解读偏差。"

        return YaoAnalysis(
            position=position,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=analysis,
            advice=advice,
            risks=risks,
        )

    def _generate_local_analysis(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
        plain_explanation: str = "",
    ) -> YaoAnalysis:
        question = hexagram_context.question
        hexagram_name = hexagram_context.hexagram_name
        subject = question.raw_question
        brief_yao_ci = _brief_line_text(yao_ci)
        templates = {
            YaoPosition.INITIAL: (
                "从{role}看，{hexagram}提醒先确认问题的根本条件。"
                "对于“{subject}”，当前重点是看清外部环境、真实约束和起步位置。",
                "先写下必须满足的前置条件，再决定是否推进。",
                "主要风险：环境判断不足，容易把愿望当作现实条件。",
            ),
            YaoPosition.SECOND: (
                "从{role}看，{hexagram}要求盘点可用资源。"
                "爻辞“{yao_ci}”提示要把人、钱、时间和支持者放到同一张表里评估。",
                "优先确认最关键的一项资源是否稳定，再安排下一步。",
                "主要风险：资源分散或承诺不清，导致执行中途失速。",
            ),
            YaoPosition.THIRD: (
                "从{role}看，{hexagram}强调行动前的风险校验。"
                "爻辞“{yao_ci}”提醒推进时要保持警觉，避免只看到机会。",
                "把最坏情况、止损线和复盘节点提前写清楚。",
                "主要风险：过度自信、节奏过急，或忽略连续投入带来的压力。",
            ),
            YaoPosition.FOURTH: (
                "从{role}看，{hexagram}关注关键转折点。"
                "这一步不只是做或不做，而是判断何时进、何时退、何时调整策略。",
                "设计一个小规模试点，用真实反馈决定是否扩大投入。",
                "主要风险：没有阶段门，导致该调整时继续硬推。",
            ),
            YaoPosition.FIFTH: (
                "从{role}看，{hexagram}要求把短期选择放进长期方向里审视。"
                "判断这件事是否强化您的核心能力、关系网络和长期位置。",
                "选择一个能积累复利的主方向，避免被短期收益牵着走。",
                "主要风险：只看眼前结果，忽略长期机会成本。",
            ),
            YaoPosition.TOP: (
                "从{role}看，{hexagram}提醒关注终局和过度扩张。"
                "爻辞“{yao_ci}”适合用来检查成功后、失败后以及极端情况下的后果。",
                "提前设定退出条件、复盘时间和纠偏动作。",
                "主要风险：走到极端后才意识到成本过高，回旋空间变小。",
            ),
        }
        analysis, advice, risks = templates[self.position]
        if plain_explanation:
            analysis = f"{analysis} 白话提示：{plain_explanation}"

        return YaoAnalysis(
            position=self.position.value,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=analysis.format(
                role=self.position.fused_role,
                hexagram=hexagram_name,
                subject=subject,
                yao_ci=brief_yao_ci,
            ),
            advice=advice,
            risks=risks,
        )


class YaoAgentOrchestrator:
    def __init__(
        self,
        llm_call: Optional[Callable[[str, str], str]] = None,
        max_workers: int = 6,
    ):
        self._llm_call = llm_call
        self._max_workers = max_workers
        self._agents = {
            pos: YaoAgent(YaoAgentConfig(position=pos, llm_call=llm_call))
            for pos in YaoPosition
        }

    def analyze_all(
        self,
        hexagram_context: HexagramContext,
        line_data: Optional[dict[str, Any]] = None,
        models_config: Optional[dict] = None,
    ) -> list[YaoAnalysis]:
        """Run analysis for all six yao positions.

        Args:
            hexagram_context: Context from scene router.
            line_data: Optional line data from DataLoader (deprecated, uses hexagram_context)
            models_config: Optional models.json for multi-model support

        Returns:
            List of 6 YaoAnalysis objects.

        Raises:
            PartialFailureError: If some positions fail but at least one succeeds.
            ValueError: If all positions fail or no line data available.
        """
        hexagram_data = hexagram_context.hexagram_data
        lines = hexagram_data.get("lines", [])

        if not lines:
            raise ValueError("No line data available in hexagram_context")

        results: dict[int, YaoAnalysis] = {}
        failed_positions: list[int] = []
        successful_positions: list[int] = []

        def analyze_position(index: int, pos: YaoPosition) -> YaoAnalysis:
            line_data_item = lines[index]
            if not isinstance(line_data_item, dict):
                line_data_item = {
                    "line_name": f"第{pos.name_cn}",
                    "yao_ci": str(line_data_item),
                }

            # Create agent-specific config if models_config provided.
            if models_config:
                yao_config = YaoAgentConfig.from_models_config(models_config, pos.value)
                if self._llm_call:
                    yao_config.llm_call = self._llm_call
                agent = YaoAgent(yao_config)
            else:
                agent = self._agents[pos]

            return agent.analyze(hexagram_context, line_data_item)

        futures = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for i, pos in enumerate(YaoPosition):
                print(f"[3/4] 分析六爻中 ({i + 1}/6)...")
                if i >= len(lines):
                    failed_positions.append(pos.value)
                    continue
                futures[executor.submit(analyze_position, i, pos)] = pos

            for future in as_completed(futures):
                pos = futures[future]
                try:
                    results[pos.value] = future.result()
                    successful_positions.append(pos.value)
                except Exception:
                    failed_positions.append(pos.value)

        if not successful_positions:
            raise ValueError("All yao position analyses failed")

        failed_positions.sort()
        successful_positions.sort()

        if failed_positions:
            raise PartialFailureError(
                failed_positions=failed_positions,
                successful_positions=successful_positions,
                partial_results=results,
            )

        return [results[pos.value] for pos in YaoPosition]

    def get_agent(self, position: YaoPosition) -> YaoAgent:
        """Get the YaoAgent for a specific position."""
        return self._agents[position]


def get_all_system_prompts() -> dict[int, str]:
    """Get system prompts for all six yao positions.

    Returns:
        Dict mapping position (1-6) to system prompt string.
    """
    return {pos.value: build_system_prompt(pos) for pos in YaoPosition}
