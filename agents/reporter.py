import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.hu_gua import calculate_hu_gua, calculate_trigram_value
from core.models import (
    DecisionReport,
    HexagramContext,
    QuestionContext,
    YaoAnalysis,
)

logger = logging.getLogger(__name__)


TRIGRAM_NAMES = {
    0: "坤",
    1: "震",
    2: "坎",
    3: "兑",
    4: "巽",
    5: "离",
    6: "艮",
    7: "乾",
}

TRIGRAM_MEANINGS = {
    0: "坤为地 - 柔顺、承载、包容",
    1: "震为雷 - 震动、行动、起始",
    2: "坎为水 - 险陷、智慧、流动",
    3: "兑为泽 - 喜悦、沟通、收获",
    4: "巽为风 - 顺从、渗透、时机",
    5: "离为火 - 明亮、依附、文明",
    6: "艮为山 - 停止、稳固、阻碍",
    7: "乾为天 - 刚健、自强不息",
}


def get_trigram_name(trigram_id: int) -> str:
    """Get trigram name from ID (0-7)."""
    return TRIGRAM_NAMES.get(trigram_id, "未知")


def get_trigram_meaning(trigram_id: int) -> str:
    """Get trigram meaning from ID (0-7)."""
    return TRIGRAM_MEANINGS.get(trigram_id, "未知含义")


@dataclass
class ReporterConfig:
    """Configuration for ReporterAgent."""

    llm_call: Optional[Callable[[str, str], str]] = None
    include_hu_gua: bool = True


class ReporterAgent:
    """Agent for generating final decision reference reports.

    Integrates hexagram analysis, yao position insights, and hu_gua
    (mutual hexagram) analysis into a comprehensive decision report.
    """

    def __init__(self, config: ReporterConfig):
        self._llm_call = config.llm_call
        self._include_hu_gua = config.include_hu_gua

    def generate_report(
        self,
        question: QuestionContext,
        hexagram_context: HexagramContext,
        yao_analyses: list[YaoAnalysis],
    ) -> DecisionReport:
        """Generate final decision reference report.

        Args:
            question: Question context from QiguaAgent.
            hexagram_context: Hexagram context from SceneRouter.
            yao_analyses: List of 6 YaoAnalysis from YaoAgentOrchestrator.

        Returns:
            DecisionReport with all analysis sections.
        """
        hu_gua_analysis = None
        if self._include_hu_gua:
            hu_gua_analysis = self._generate_hu_gua_analysis(hexagram_context)

        if self._llm_call is None:
            return self._generate_mock_report(
                question, hexagram_context, yao_analyses, hu_gua_analysis
            )

        overall_advice, key_risks, timing_judgment, next_steps = self._llm_generate(
            question, hexagram_context, yao_analyses, hu_gua_analysis
        )

        return DecisionReport(
            question=question,
            hexagram=hexagram_context,
            yao_analyses=yao_analyses,
            overall_advice=overall_advice,
            key_risks=key_risks,
            timing_judgment=timing_judgment,
            next_steps=next_steps,
            hu_gua_analysis=hu_gua_analysis,
        )

    def _generate_hu_gua_analysis(self, hexagram_context: HexagramContext) -> str:
        hexagram_data = hexagram_context.hexagram_data
        lines = hexagram_data.get("lines", [])

        if not lines or len(lines) < 6:
            return "互卦分析需要完整的六爻数据"

        yao_values = []
        for line in lines:
            if isinstance(line, dict):
                yao_name = line.get("yao_name", "")
                if (
                    "九" in yao_name
                    or yao_name.startswith("初九")
                    or yao_name.startswith("九")
                    or yao_name.startswith("上九")
                ):
                    yao_values.append(1)
                else:
                    yao_values.append(0)
            else:
                yao_values.append(1 if str(line).startswith("九") else 0)

        if len(yao_values) < 6:
            return "互卦分析需要完整的六爻数据"

        hu_gua_id = calculate_hu_gua(hexagram_context.hexagram_id, yao_values)

        lower_yao = [yao_values[1], yao_values[2], yao_values[3]]
        upper_yao = [yao_values[2], yao_values[3], yao_values[4]]

        lower_trigram = calculate_trigram_value(lower_yao)
        upper_trigram = calculate_trigram_value(upper_yao)

        lower_trigram_name = get_trigram_name(lower_trigram)
        upper_trigram_name = get_trigram_name(upper_trigram)
        lower_trigram_meaning = get_trigram_meaning(lower_trigram)
        upper_trigram_meaning = get_trigram_meaning(upper_trigram)

        if self._llm_call:
            try:
                hu_gua_interpretation = self._llm_call(
                    "你是易经互卦分析专家，负责解读互卦的内在含义。",
                    f"""本卦：{hexagram_context.hexagram_name}（第{hexagram_context.hexagram_id}卦）
 互卦：第{hu_gua_id}卦
 互卦下卦（内卦）：{lower_trigram_name} - {lower_trigram_meaning}
 互卦上卦（外卦）：{upper_trigram_name} - {upper_trigram_meaning}

 请解读互卦对当前决策的内在启示。""",
                )
            except Exception as e:
                logger.warning(f"Hu Gua LLM call failed: {e}, using fallback")
                hu_gua_interpretation = (
                    f"互卦揭示了事物内部的相互作用和转化趋势。"
                    f"下卦{lower_trigram_name}代表内在基础和初始状态，"
                    f"上卦{upper_trigram_name}代表外在表现和发展方向。"
                )
        else:
            hu_gua_interpretation = (
                f"互卦揭示了事物内部的相互作用和转化趋势。"
                f"下卦{lower_trigram_name}代表内在基础和初始状态，"
                f"上卦{upper_trigram_name}代表外在表现和发展方向。"
            )

        return self._format_hu_gua_section(
            hexagram_context.hexagram_name,
            hexagram_context.hexagram_id,
            hu_gua_id,
            lower_trigram_name,
            upper_trigram_name,
            lower_trigram_meaning,
            upper_trigram_meaning,
            hu_gua_interpretation,
        )

    def _format_hu_gua_section(
        self,
        hexagram_name: str,
        hexagram_id: int,
        hu_gua_id: int,
        lower_trigram_name: str,
        upper_trigram_name: str,
        lower_trigram_meaning: str,
        upper_trigram_meaning: str,
        hu_gua_interpretation: str,
    ) -> str:
        """Format hu_gua analysis section."""
        return f"""## 互卦分析

本卦：{hexagram_name}（第{hexagram_id}卦）
互卦：第{hu_gua_id}卦

互卦解读：
- 下卦（内卦）：{lower_trigram_name} - {lower_trigram_meaning}
- 上卦（外卦）：{upper_trigram_name} - {upper_trigram_meaning}
- 内在启示：{hu_gua_interpretation}"""

    def _generate_mock_report(
        self,
        question: QuestionContext,
        hexagram_context: HexagramContext,
        yao_analyses: list[YaoAnalysis],
        hu_gua_analysis: Optional[str],
    ) -> DecisionReport:
        """Generate mock report when LLM is not available."""
        return DecisionReport(
            question=question,
            hexagram=hexagram_context,
            yao_analyses=yao_analyses,
            overall_advice=f"基于{hexagram_context.hexagram_name}的综合建议",
            key_risks="需要关注的主要风险",
            timing_judgment="时机判断",
            next_steps=["步骤 1", "步骤 2", "步骤 3"],
            hu_gua_analysis=hu_gua_analysis,
        )

    def _generate_mock_report_data(
        self,
        question: QuestionContext,
        hexagram_context: HexagramContext,
        yao_analyses: list[YaoAnalysis],
    ) -> tuple[str, str, str, list[str]]:
        hexagram_name = hexagram_context.hexagram_name
        hexagram_id = hexagram_context.hexagram_id

        yao_highlights = [ya.advice for ya in yao_analyses if ya.advice][:3]
        if not yao_highlights:
            yao_highlights = ["审慎行事", "把握时机", "注重积累"]

        overall_advice = (
            f"根据{hexagram_name}（第{hexagram_id}卦）的启示，建议您："
            + "。".join(yao_highlights)
            + "。易经强调因时而动，顺势而为。"
        )

        risks = [ya.risks for ya in yao_analyses if ya.risks and ya.risks != "待评估"][
            :2
        ]
        if not risks:
            risks = ["需注意潜在风险", "建议谨慎评估"]
        key_risks = "；".join(risks)

        timing_keywords = {
            "乾": "时机成熟，宜积极进取",
            "坤": "时机未到，宜静待良机",
            "屯": "初创阶段，宜稳扎稳打",
            "蒙": "学习阶段，宜耐心积累",
            "需": "等待时机，不宜急躁",
            "讼": "争执阶段，宜和解为主",
            "师": "行动阶段，宜果断决策",
            "比": "合作阶段，宜广结善缘",
        }
        timing_judgment = timing_keywords.get(
            hexagram_name[0], "根据当前形势，宜审时度势，灵活应对"
        )

        next_steps = []
        for ya in yao_analyses[:3]:
            if ya.advice and len(ya.advice) > 5:
                next_steps.append(ya.advice)
        if not next_steps:
            next_steps = ["分析当前形势", "制定详细计划", "逐步实施方案"]

        return (overall_advice, key_risks, timing_judgment, next_steps[:5])

    def _llm_generate(
        self,
        question: QuestionContext,
        hexagram_context: HexagramContext,
        yao_analyses: list[YaoAnalysis],
        hu_gua_analysis: Optional[str],
    ) -> tuple[str, str, str, list[str]]:
        yao_summary = "\n".join(
            [
                f"【{a.line_name}】\n  爻辞：{a.yao_ci}\n  解读：{a.analysis}\n  建议：{a.advice}\n  风险：{a.risks}"
                for a in yao_analyses
            ]
        )

        hu_gua_section = f"\n\n{hu_gua_analysis}" if hu_gua_analysis else ""

        user_prompt = f"""用户问题：{question.raw_question}
问题类型：{question.question_type}
背景：{question.background}
期望结果：{question.expected_outcome}
风险承受：{question.risk_tolerance}

本卦：{hexagram_context.hexagram_name}（第{hexagram_context.hexagram_id}卦）
匹配原因：{hexagram_context.match_reason}

六爻完整分析：
{yao_summary}
{hu_gua_section}

请基于以上六爻分析，生成决策参考报告。

必须严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "overall_advice": "综合六爻解读，给出整体建议（2-3句话）",
  "key_risks": "提炼主要风险点，用分号分隔",
  "timing_judgment": "分析当前行动时机（1-2句话）",
  "next_steps": ["步骤1", "步骤2", "步骤3"]
}}"""

        try:
            assert self._llm_call is not None, "LLM call should not be None"
            response = self._llm_call(
                "你是决策报告官，负责综合六爻分析生成结构化的决策参考报告。",
                user_prompt,
            )
            logger.info("LLM call succeeded, parsing response...")
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            logger.warning("Falling back to mock report generation")
            return self._generate_mock_report_data(
                question, hexagram_context, yao_analyses
            )

    def _parse_llm_response(self, response: str) -> tuple[str, str, str, list[str]]:
        """Parse LLM response into report components."""
        response = self._filter_think_content(response)

        json_result = self._try_parse_json(response)
        if json_result:
            return json_result

        return self._parse_text_response(response)

    def _filter_think_content(self, response: str) -> str:
        """Remove think/reasoning blocks from response."""
        response = re.sub(r"hlen.*?hlen", "", response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(
            r"\|think\|.*?\|think\|", "", response, flags=re.DOTALL | re.IGNORECASE
        )
        response = re.sub(
            r"\(think\).*?\(think\)", "", response, flags=re.DOTALL | re.IGNORECASE
        )
        response = re.sub(
            r"\[think\].*?\[think\]", "", response, flags=re.DOTALL | re.IGNORECASE
        )
        return response.strip()

    def _try_parse_json(
        self, response: str
    ) -> Optional[tuple[str, str, str, list[str]]]:
        json_str = self._extract_json_object(response)
        if not json_str:
            return None

        try:
            data = json.loads(json_str)
            overall_advice = data.get("overall_advice") or data.get("综合建议", "")
            key_risks = data.get("key_risks") or data.get("关键风险", "")
            timing_judgment = data.get("timing_judgment") or data.get("时机判断", "")
            next_steps = data.get("next_steps") or data.get("下一步行动", [])

            if isinstance(key_risks, list):
                key_risks = "；".join(key_risks)
            if isinstance(next_steps, str):
                next_steps = [
                    s.strip() for s in re.split(r"[;\n]", next_steps) if s.strip()
                ]

            if overall_advice or key_risks or timing_judgment or next_steps:
                return (
                    overall_advice or "请综合考虑各方因素，审慎决策",
                    key_risks or "建议全面评估潜在风险",
                    timing_judgment or "建议根据具体情况选择合适时机",
                    next_steps[:5]
                    if next_steps
                    else ["评估当前形势", "制定实施计划", "分阶段推进"],
                )
        except json.JSONDecodeError:
            pass
        return None

    def _extract_json_object(self, response: str) -> Optional[str]:
        brace_count = 0
        start = -1
        for i, char in enumerate(response):
            if char == "{":
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and start >= 0:
                    return response[start : i + 1]
        return None

    def _parse_text_response(self, response: str) -> tuple[str, str, str, list[str]]:
        """Parse text format response as fallback."""
        sections = {
            "综合建议": "",
            "关键风险": "",
            "时机判断": "",
            "下一步行动": "",
        }
        current_section = None

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            for section_name in sections:
                if section_name in line and ("：" in line or ":" in line):
                    current_section = section_name
                    if "：" in line:
                        sections[section_name] = line.split("：", 1)[1].strip()
                    elif ":" in line:
                        sections[section_name] = line.split(":", 1)[1].strip()
                    break
            else:
                if current_section and line:
                    sections[current_section] += " " + line

        next_steps = []
        steps_text = sections.get("下一步行动", "")
        if steps_text:
            for line in steps_text.split("\n"):
                line = line.strip()
                if line and (line.startswith("-") or line.startswith("•")):
                    next_steps.append(line.lstrip("-•").strip())
                elif line and any(c.isdigit() for c in line[:2]):
                    next_steps.append(line)

        overall_advice = sections.get("综合建议", "").strip()
        if not overall_advice or len(overall_advice) < 10:
            overall_advice = (
                response.strip()[:300] if response else "请综合考虑各方因素，审慎决策"
            )

        key_risks = sections.get("关键风险", "").strip()
        if not key_risks or len(key_risks) < 5:
            key_risks = "建议全面评估潜在风险，做好风险防控准备"

        timing_judgment = sections.get("时机判断", "").strip()
        if not timing_judgment or len(timing_judgment) < 5:
            timing_judgment = "建议根据具体情况，选择合适的时机行动"

        if not next_steps:
            next_steps = ["评估当前形势和资源", "制定详细实施计划", "分阶段推进落实"]

        return (overall_advice, key_risks, timing_judgment, next_steps[:5])

    def format_report_text(self, report: DecisionReport) -> str:
        """Format decision report as readable text.

        Args:
            report: DecisionReport to format.

        Returns:
            Formatted report text.
        """
        lines = [
            f"# 决策参考报告",
            f"",
            f"**问题**：{report.question.raw_question}",
            f"",
            f"**卦象**：{report.hexagram.hexagram_name}（第{report.hexagram.hexagram_id}卦）",
            f"",
            f"## 六爻分析",
        ]

        for ya in report.yao_analyses:
            lines.append(f"### {ya.line_name}")
            lines.append(f"- 爻辞：{ya.yao_ci}")
            lines.append(f"- 解读：{ya.analysis}")
            lines.append(f"- 建议：{ya.advice}")
            lines.append(f"- 风险：{ya.risks}")
            lines.append("")

        if report.hu_gua_analysis:
            lines.append(report.hu_gua_analysis)
            lines.append("")

        lines.extend(
            [
                f"## 综合建议",
                f"{report.overall_advice}",
                f"",
                f"## 关键风险",
                f"{report.key_risks}",
                f"",
                f"## 时机判断",
                f"{report.timing_judgment}",
                f"",
                f"## 下一步行动",
            ]
        )

        for i, step in enumerate(report.next_steps, 1):
            lines.append(f"{i}. {step}")

        return "\n".join(lines)
