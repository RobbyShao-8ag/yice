"""
YaoAgents for the yice decision system.

Six yao position agents that analyze hexagram lines with fused
traditional and modern role definitions. Each agent focuses on
a specific aspect of the decision process.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.errors import PartialFailureError
from core.models import HexagramContext, YaoAnalysis, YaoPosition


def _parse_llm_response(response: str) -> dict[str, str]:
    response = _filter_think_blocks(response)

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


def _filter_think_blocks(response: str) -> str:
    """Remove think/reasoning blocks from LLM response."""
    import re

    # Pattern 1: hlen content hlen (most common)
    response = re.sub(
        r"^hlen\s*\n(.*?\n)?hlen\s*$",
        "",
        response,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Pattern 2: Inline hlen blocks
    response = re.sub(
        r"hlen\s*(.*?)\s*hlen",
        "",
        response,
        flags=re.DOTALL,
    )

    # Pattern 3: Line-by-line cleanup for any remaining think markers
    lines = response.split("\n")
    result = []
    in_think = False

    for line in lines:
        stripped = line.strip()

        # Start of think block
        if stripped.lower() == "hlen" or "hlen" in stripped[:10].lower():
            in_think = True
            continue

        # End of think block
        if stripped.lower() == "hlen" or "hlen" in stripped[-10:].lower():
            in_think = False
            continue

        # Skip lines inside think block
        if in_think:
            continue

        # Skip standalone markers
        if stripped.lower() in ["hlen", "hlen", "think", "|think|"]:
            continue

        result.append(line)

    filtered = "\n".join(result)

    # Debug
    if len(filtered) < len(response):
        print(f"[FILTER] {len(response)} -> {len(filtered)} chars")

    return filtered


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

        if self._llm_call is None:
            return YaoAnalysis(
                position=self.position.value,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis=f"[{self.position.fused_role}] 待 LLM 分析",
                advice=f"[{self.position.role}] 待生成建议",
                risks=f"[{self.position.traditional_meaning}] 待风险评估",
            )

        user_prompt = self._build_user_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self._system_prompt, user_prompt)

        return self._parse_response(self.position.value, line_name, yao_ci, response)

    def _build_user_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
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

请从{self.position.fused_role}的角度分析此爻辞对用户问题的启示。"""


def _parse_response(
    self,
    position: int,
    line_name: str,
    yao_ci: str,
    response: str,
) -> YaoAnalysis:
    sections = _parse_llm_response(response)
    return YaoAnalysis(
        position=position,
        line_name=line_name,
        yao_ci=yao_ci,
        analysis=sections["解读"].strip() or response.strip(),
        advice=sections["建议"].strip() or "",
        risks=sections["风险"].strip() or "",
    )


class YaoAgent1:
    """初爻 - 环境感知（潜龙勿用）"""

    SYSTEM_PROMPT = """你是初爻分析官，对应基础环境层。

传统含义：根本
现代映射：环境感知
融合角色：基础环境层 - 识别问题根本、环境基调

你的任务是：
1. 分析当前环境的基础条件
2. 识别潜在的信号和趋势
3. 评估是否适合行动

记住"潜龙勿用"的智慧：时机未到时，宜静待而非冒进。"""

    def __init__(self, config: YaoAgentConfig):
        self.position = YaoPosition.INITIAL
        self._config = config
        self._llm_call = config.llm_call

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]

        if self._llm_call is None:
            return YaoAnalysis(
                position=1,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis="[基础环境层] 待 LLM 分析",
                advice="[环境感知] 待生成建议",
                risks="[根本] 待风险评估",
            )

        prompt = self._build_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self.SYSTEM_PROMPT, prompt)
        return self._parse_response(line_name, yao_ci, response)

    def _build_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
    ) -> str:
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

请从基础环境层的角度，分析当前环境的基础条件、潜在信号和行动时机。"""

    def _parse_response(
        self,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)
        return YaoAnalysis(
            position=1,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=sections["解读"].strip() or response.strip(),
            advice=sections["建议"].strip() or "",
            risks=sections["风险"].strip() or "",
        )


class YaoAgent2:
    """二爻 - 资源配置（见龙在田）"""

    SYSTEM_PROMPT = """你是二爻分析官，对应内部资源层。

传统含义：内中馈
现代映射：资源配置
融合角色：内部资源层 - 评估内部条件、资源匹配

你的任务是：
1. 评估现有资源是否充足
2. 分析资源配置是否合理
3. 识别资源缺口

记住"见龙在田"的智慧：展现能力，寻求支持。"""

    def __init__(self, config: YaoAgentConfig):
        self.position = YaoPosition.SECOND
        self._config = config
        self._llm_call = config.llm_call

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]

        if self._llm_call is None:
            return YaoAnalysis(
                position=2,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis="[内部资源层] 待 LLM 分析",
                advice="[资源配置] 待生成建议",
                risks="[内中馈] 待风险评估",
            )

        prompt = self._build_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self.SYSTEM_PROMPT, prompt)
        return self._parse_response(line_name, yao_ci, response)

    def _build_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
    ) -> str:
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

请从内部资源层的角度，评估现有资源的充足性、配置合理性及资源缺口。"""

    def _parse_response(
        self,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)
        return YaoAnalysis(
            position=2,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=sections["解读"].strip() or response.strip(),
            advice=sections["建议"].strip() or "",
            risks=sections["风险"].strip() or "",
        )


class YaoAgent3:
    """三爻 - 风险评估（君子终日乾乾）"""

    SYSTEM_PROMPT = """你是三爻分析官，对应行动执行层。

传统含义：君子终日乾乾
现代映射：风险评估
融合角色：行动执行层 - 行动中的风险与努力

你的任务是：
1. 识别行动中的潜在风险
2. 评估风险等级和影响
3. 提供谨慎的行动建议

记住"君子终日乾乾"的智慧：白天勤奋努力，夜晚警惕反省。"""

    def __init__(self, config: YaoAgentConfig):
        self.position = YaoPosition.THIRD
        self._config = config
        self._llm_call = config.llm_call

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]

        if self._llm_call is None:
            return YaoAnalysis(
                position=3,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis="[行动执行层] 待 LLM 分析",
                advice="[风险评估] 待生成建议",
                risks="[君子终日乾乾] 待风险评估",
            )

        prompt = self._build_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self.SYSTEM_PROMPT, prompt)
        return self._parse_response(line_name, yao_ci, response)

    def _build_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
    ) -> str:
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

请从行动执行层的角度，识别潜在风险、评估风险等级并提供谨慎的行动建议。"""

    def _parse_response(
        self,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)
        return YaoAnalysis(
            position=3,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=sections["解读"].strip() or response.strip(),
            advice=sections["建议"].strip() or "",
            risks=sections["风险"].strip() or "",
        )


class YaoAgent4:
    """四爻 - 策略执行（或跃在渊）"""

    SYSTEM_PROMPT = """你是四爻分析官，对应关键转折层。

传统含义：门阙
现代映射：策略执行
融合角色：关键转折层 - 决策关键点、策略调整

你的任务是：
1. 识别关键决策点
2. 评估进退策略
3. 提供灵活的行动建议

记住"或跃在渊"的智慧：可进可退，审时度势。"""

    def __init__(self, config: YaoAgentConfig):
        self.position = YaoPosition.FOURTH
        self._config = config
        self._llm_call = config.llm_call

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]

        if self._llm_call is None:
            return YaoAnalysis(
                position=4,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis="[关键转折层] 待 LLM 分析",
                advice="[策略执行] 待生成建议",
                risks="[门阙] 待风险评估",
            )

        prompt = self._build_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self.SYSTEM_PROMPT, prompt)
        return self._parse_response(line_name, yao_ci, response)

    def _build_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
    ) -> str:
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

请从关键转折层的角度，识别关键决策点、评估进退策略并提供灵活的行动建议。"""

    def _parse_response(
        self,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)
        return YaoAnalysis(
            position=4,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=sections["解读"].strip() or response.strip(),
            advice=sections["建议"].strip() or "",
            risks=sections["风险"].strip() or "",
        )


class YaoAgent5:
    """五爻 - 长期规划（飞龙在天）"""

    SYSTEM_PROMPT = """你是五爻分析官，对应核心决策层。

传统含义：君位
现代映射：长期规划
融合角色：核心决策层 - 主导方向、长远影响

你的任务是：
1. 制定长期战略方向
2. 评估决策的长远影响
3. 提供核心决策建议

记住"飞龙在天"的智慧：居高临下，把握大局。"""

    @property
    def system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def __init__(self, config: YaoAgentConfig):
        self.position = YaoPosition.FIFTH
        self._config = config
        self._llm_call = config.llm_call

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]

        if self._llm_call is None:
            return YaoAnalysis(
                position=5,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis="[核心决策层] 待 LLM 分析",
                advice="[长期规划] 待生成建议",
                risks="[君位] 待风险评估",
            )

        prompt = self._build_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self.SYSTEM_PROMPT, prompt)
        return self._parse_response(line_name, yao_ci, response)

    def _build_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
    ) -> str:
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

请从核心决策层的角度，制定长期战略方向、评估决策的长远影响并提供核心决策建议。"""

    def _parse_response(
        self,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)
        return YaoAnalysis(
            position=5,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=sections["解读"].strip() or response.strip(),
            advice=sections["建议"].strip() or "",
            risks=sections["风险"].strip() or "",
        )


class YaoAgent6:
    """上爻 - 结果复盘（亢龙有悔）"""

    SYSTEM_PROMPT = """你是上爻分析官，对应终局反思层。

传统含义：亢龙有悔
现代映射：结果复盘
融合角色：终局反思层 - 极端情况、反思总结

你的任务是：
1. 评估极端情况的风险
2. 提供反思和警示
3. 总结经验和教训

记住"亢龙有悔"的智慧：物极必反，适可而止。"""

    def __init__(self, config: YaoAgentConfig):
        self.position = YaoPosition.TOP
        self._config = config
        self._llm_call = config.llm_call

    def analyze(
        self,
        hexagram_context: HexagramContext,
        line_data: dict[str, Any],
    ) -> YaoAnalysis:
        required_fields = ["line_name", "yao_ci"]
        missing = [f for f in required_fields if f not in line_data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        line_name = line_data["line_name"]
        yao_ci = line_data["yao_ci"]

        if self._llm_call is None:
            return YaoAnalysis(
                position=6,
                line_name=line_name,
                yao_ci=yao_ci,
                analysis="[终局反思层] 待 LLM 分析",
                advice="[结果复盘] 待生成建议",
                risks="[亢龙有悔] 待风险评估",
            )

        prompt = self._build_prompt(hexagram_context, line_name, yao_ci)
        response = self._llm_call(self.SYSTEM_PROMPT, prompt)
        return self._parse_response(line_name, yao_ci, response)

    def _build_prompt(
        self,
        hexagram_context: HexagramContext,
        line_name: str,
        yao_ci: str,
    ) -> str:
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

请从终局反思层的角度，评估极端情况的风险、提供反思警示并总结经验教训。"""

    def _parse_response(
        self,
        line_name: str,
        yao_ci: str,
        response: str,
    ) -> YaoAnalysis:
        sections = _parse_llm_response(response)

        return YaoAnalysis(
            position=6,
            line_name=line_name,
            yao_ci=yao_ci,
            analysis=sections["解读"] or response,
            advice=sections["建议"] or "待补充",
            risks=sections["风险"] or "待补充",
        )


class YaoAgentOrchestrator:
    def __init__(
        self,
        llm_call: Optional[Callable[[str, str], str]] = None,
    ):
        self._llm_call = llm_call
        self._agents = {
            YaoPosition.INITIAL: YaoAgent1(
                YaoAgentConfig(position=YaoPosition.INITIAL, llm_call=llm_call)
            ),
            YaoPosition.SECOND: YaoAgent2(
                YaoAgentConfig(position=YaoPosition.SECOND, llm_call=llm_call)
            ),
            YaoPosition.THIRD: YaoAgent3(
                YaoAgentConfig(position=YaoPosition.THIRD, llm_call=llm_call)
            ),
            YaoPosition.FOURTH: YaoAgent4(
                YaoAgentConfig(position=YaoPosition.FOURTH, llm_call=llm_call)
            ),
            YaoPosition.FIFTH: YaoAgent5(
                YaoAgentConfig(position=YaoPosition.FIFTH, llm_call=llm_call)
            ),
            YaoPosition.TOP: YaoAgent6(
                YaoAgentConfig(position=YaoPosition.TOP, llm_call=llm_call)
            ),
        }

    def _create_llm_call(self, config: YaoAgentConfig) -> Callable[[str, str], str]:
        """Create LLM call function for a specific provider/model.

        Args:
            config: YaoAgentConfig with provider/model

        Returns:
            LLM call function
        """

        # Placeholder - actual implementation depends on core.llm_client
        # This method should be overridden or configured externally
        def llm_call(system_prompt: str, user_prompt: str) -> str:
            raise NotImplementedError(
                f"LLM call not configured for {config.provider}/{config.model}. "
                "Configure llm_call in YaoAgentConfig or use from_models_config."
            )

        return llm_call

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

        for i, pos in enumerate(YaoPosition):
            print(f"[3/4] 分析六爻中 ({i + 1}/6)...")
            if i >= len(lines):
                failed_positions.append(pos.value)
                continue

            line_data_item = lines[i]
            if not isinstance(line_data_item, dict):
                line_data_item = {
                    "line_name": f"第{pos.name_cn}",
                    "yao_ci": str(line_data_item),
                }

            try:
                # Create agent-specific config if models_config provided
                if models_config:
                    yao_config = YaoAgentConfig.from_models_config(
                        models_config, pos.value
                    )
                    # Use shared llm_call if available, otherwise use placeholder
                    if self._llm_call:
                        yao_config.llm_call = self._llm_call
                    agent = YaoAgent(yao_config)
                else:
                    # Fallback to shared config
                    agent = self._agents[pos]

                results[pos.value] = agent.analyze(hexagram_context, line_data_item)
                successful_positions.append(pos.value)
            except (ValueError, KeyError, TypeError) as e:
                failed_positions.append(pos.value)

        if not successful_positions:
            raise ValueError("All yao position analyses failed")

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
