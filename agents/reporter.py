import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.hu_gua import calculate_hu_gua, calculate_trigram_value
from core.llm_filters import filter_think_content
from core.models import (
    DecisionReport,
    HexagramContext,
    QuestionContext,
    YaoAnalysis,
)
from core.yao_lines import get_yao_values

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


def _strip_sentence_end(text: str) -> str:
    return text.strip().rstrip("。.!！？；; ")


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

        report_data = self._llm_generate(
            question, hexagram_context, yao_analyses, hu_gua_analysis
        )

        return DecisionReport(
            question=question,
            hexagram=hexagram_context,
            yao_analyses=yao_analyses,
            overall_advice=report_data["overall_advice"],
            key_risks=report_data["key_risks"],
            timing_judgment=report_data["timing_judgment"],
            next_steps=report_data["next_steps"],
            hu_gua_analysis=hu_gua_analysis,
            decision_tendency=report_data["decision_tendency"],
            core_reasons=report_data["core_reasons"],
            option_comparison=report_data["option_comparison"],
            decision_conditions=report_data["decision_conditions"],
            stop_conditions=report_data["stop_conditions"],
            missing_information=report_data["missing_information"],
            review_trigger=report_data["review_trigger"],
            confidence=report_data["confidence"],
        )

    def _generate_hu_gua_analysis(self, hexagram_context: HexagramContext) -> str:
        hexagram_data = hexagram_context.hexagram_data
        lines = hexagram_data.get("lines", [])

        if not lines or len(lines) < 6:
            return "互卦分析需要完整的六爻数据"

        yao_values = get_yao_values(hexagram_data)

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
        overall_advice, key_risks, timing_judgment, next_steps = (
            self._generate_mock_report_data(question, hexagram_context, yao_analyses)
        )
        decision_data = self._build_decision_v2(
            question,
            hexagram_context,
            yao_analyses,
            overall_advice,
            key_risks,
            timing_judgment,
            next_steps,
        )
        overall_advice = decision_data.pop("_overall_advice", overall_advice)
        timing_judgment = decision_data.pop("_timing_judgment", timing_judgment)
        return DecisionReport(
            question=question,
            hexagram=hexagram_context,
            yao_analyses=yao_analyses,
            overall_advice=overall_advice,
            key_risks=key_risks,
            timing_judgment=timing_judgment,
            next_steps=next_steps,
            hu_gua_analysis=hu_gua_analysis,
            **decision_data,
        )

    def _build_decision_v2(
        self,
        question: QuestionContext,
        hexagram_context: HexagramContext,
        yao_analyses: list[YaoAnalysis],
        overall_advice: str,
        key_risks: str,
        timing_judgment: str,
        next_steps: list[str],
    ) -> dict[str, Any]:
        """Build a useful deterministic decision contract for local/fallback mode."""
        full_text = " ".join(
            [
                question.raw_question,
                question.background,
                question.constraints,
                question.expected_outcome,
                " ".join(question.extra_context.values()),
            ]
        )
        is_startup = any(
            word in full_text
            for word in ("创业", "产品", "原型", "客户", "现金流", "全职投入")
        )
        has_traction = any(
            word in full_text for word in ("原型", "试用客户", "付费客户", "已有收入")
        )
        has_runway_pressure = any(
            word in full_text for word in ("现金流", "只够", "资金有限", "亏损", "负债")
        )
        is_health = any(
            word in full_text
            for word in ("身体不舒服", "健康", "医疗", "诊断", "症状", "高强度工作")
        )
        is_legal = any(
            word in full_text for word in ("起诉", "诉讼", "合同纠纷", "违法")
        )
        is_financial_risk = any(
            word in full_text for word in ("股票", "借贷", "借款", "大部分积蓄")
        )
        is_high_stakes = is_health or is_legal or is_financial_risk
        custom_overall: Optional[str] = None
        custom_timing: Optional[str] = None

        if is_high_stakes:
            tendency = "暂缓，并先取得专业意见"
        elif is_startup or has_runway_pressure:
            tendency = "有条件推进"
        else:
            tendency = "小范围验证后推进"

        if is_health:
            core_reasons = [
                "健康风险一旦扩大，后续代价可能不可逆，不能只用工作收益衡量。",
                "当前缺少症状、持续时间和专业检查结果，系统不能代替医生判断。",
                f"{hexagram_context.hexagram_name}在此只作为停止、观察和复评的思考提示。",
            ]
            option_comparison = [
                {"option": "继续高强度工作", "benefit": "短期维持进度", "cost_or_risk": "可能加重症状并延误处理"},
                {"option": "立即降强度并就医", "benefit": "优先控制不可逆健康风险", "cost_or_risk": "短期工作安排需要调整"},
            ]
            decision_conditions = ["先停止高强度工作并安排专业就医。", "仅在专业评估允许且症状明显改善后逐步恢复工作。"]
            stop_conditions = ["症状加重或出现明显危险信号时立即停止工作并寻求急诊帮助。"]
            missing_information = ["具体症状及持续时间", "是否存在胸痛、呼吸困难、意识异常等危险信号", "医生检查与休息建议"]
            review_trigger = "完成专业医疗评估后复评；症状加重时不等待复评日期"
            next_steps[:] = ["立即降低工作强度并告知相关同事。", "尽快预约正规医疗机构评估。", "记录症状、诱因和变化，供医生判断。"]
            custom_overall = "当前应优先停止高强度工作并尽快就医，而不是继续用意志力硬撑。本系统只能提供风险整理，不能作医疗诊断。"
            custom_timing = "健康处理的时机是现在；是否恢复高强度工作应以专业评估为前提。"
        elif is_legal:
            core_reasons = ["诉讼是成本较高且相对不可逆的路径，应先确认合同、证据和回款可能。", "系统无法替代律师对时效、管辖和证据效力的判断。", f"{hexagram_context.hexagram_name}提示应先厘清争议边界，再决定升级手段。"]
            option_comparison = [
                {"option": "直接起诉", "benefit": "迅速进入强制解决程序", "cost_or_risk": "时间、费用和关系成本较高"},
                {"option": "律师函或正式催收", "benefit": "先测试对方履约意愿并固定证据", "cost_or_risk": "可能继续拖延"},
                {"option": "协商分期", "benefit": "提高短期回款可行性", "cost_or_risk": "需要新的担保和违约约束"},
            ]
            decision_conditions = ["整理合同、交付、对账、催收和对方确认欠款的证据链。", "由律师评估诉讼时效、管辖、保全价值和预计回款率。"]
            stop_conditions = ["预计诉讼成本明显高于可回收金额。", "关键证据不足且继续行动可能造成更大损失。"]
            missing_information = ["欠款金额和账龄", "合同及验收对账证据", "对方资产状况和实际回款能力"]
            review_trigger = "律师完成证据与回款可行性评估后复评"
            next_steps[:] = ["今天整理完整证据时间线。", "向对方发出有期限的正式书面催收。", "携材料咨询当地执业律师后再决定是否起诉。"]
            custom_overall = "当前不宜仅凭情绪立即起诉。先固定证据、正式催收并让律师评估回款可行性；达到诉讼条件后再升级。"
            custom_timing = "先在明确催收期限内完成证据和律师评估，避免无期限拖延，也避免准备不足时仓促起诉。"
        elif is_financial_risk:
            core_reasons = ["集中投入积蓄或继续借款会显著降低财务可逆性。", "当前缺少资产负债、现金流和最大可承受损失信息。", "高风险金融选择需要持牌专业意见和独立核验。"]
            option_comparison = [
                {"option": "集中投入或继续加杠杆", "benefit": "潜在收益放大", "cost_or_risk": "本金损失和偿债风险同步放大"},
                {"option": "限制仓位或暂停借款", "benefit": "保留安全垫和后续选择", "cost_or_risk": "可能错过部分上涨"},
            ]
            decision_conditions = ["先保留应急资金和必要生活支出。", "明确最大损失上限并取得持牌专业意见。"]
            stop_conditions = ["需要借新还旧或动用必要生活资金。", "潜在损失超过事先确定的承受上限。"]
            missing_information = ["完整资产负债表", "稳定现金流和应急资金", "最大可承受本金损失"]
            review_trigger = "完成独立财务评估和风险压力测试后复评"
            next_steps[:] = ["暂停不可逆的大额投入或新增借款。", "列出资产负债和未来12个月现金流。", "咨询持牌专业人士并比较至少三种保守方案。"]
            custom_overall = "当前建议暂缓大额集中投入或新增借款，先完成资产负债、现金流和最大损失压力测试。"
            custom_timing = "在风险边界和专业意见明确之前，不把市场波动当作必须立即行动的信号。"
        elif is_startup:
            core_reasons = [
                (
                    "已有原型或客户信号，值得继续验证，但现有信号还不足以证明稳定需求。"
                    if has_traction
                    else "尚未提供可验证的客户、收入或使用数据，不能把创业意愿当作市场证据。"
                ),
                "现金跑道限制了试错次数，应优先验证付费和获客，而不是先扩大固定投入。",
                f"{hexagram_context.hexagram_name}强调当前阶段要用里程碑控制推进节奏。",
            ]
            option_comparison = [
                {
                    "option": "立即全职投入",
                    "benefit": "推进速度最快",
                    "cost_or_risk": "现金跑道快速缩短，决策可逆性低",
                },
                {
                    "option": "限时验证后决定",
                    "benefit": "用真实付费信号换取确定性",
                    "cost_or_risk": "短期需要兼顾验证与现有收入来源",
                },
                {
                    "option": "暂不投入",
                    "benefit": "保留现金和职业安全边际",
                    "cost_or_risk": "可能错过窗口，也无法获得进一步市场证据",
                },
            ]
            decision_conditions = [
                "在 14 天内让至少 1 个试用客户形成明确付费承诺，并确认金额与付款日期。",
                "列出未来 8 周的潜在客户管道，证明获客不只依赖现有两位试用者。",
                "全职投入后仍保留不少于 3 个月的个人与项目最低现金安全垫。",
            ]
            stop_conditions = [
                "现金跑道降至 3 个月且仍没有付费客户或可验证订单。",
                "连续两轮客户验证都无法确认高频痛点、使用意愿或付费意愿。",
                "为了继续项目必须承担超出既定风险承受度的债务或不可逆成本。",
            ]
            missing_information = [
                "两个试用客户的实际使用频率、核心反馈和付费意愿",
                "每月最低支出、全职后的真实现金跑道和可削减成本",
                "未来 8 周可接触的目标客户数量与预计成交路径",
            ]
            review_trigger = "14 天验证期结束，或首位客户确认付费后立即复评"
            specific_steps = [
                "今天分别约谈两个试用客户，记录使用频率、替代方案和愿付价格。",
                "48 小时内做出现金跑道表，分别模拟不投入、半投入和全职投入三种情景。",
                "设定 14 天验证冲刺，只验证付费、留存和可复制获客三个指标。",
            ]
            next_steps[:] = specific_steps
            custom_overall = (
                f"结合{hexagram_context.hexagram_name}的阶段启示，当前更适合有条件推进，"
                "而不是立即无保留地全职投入。"
                "先用 14 天把试用信号转成付费和可复制获客证据；达到推进条件后再全职，"
                "未达到则保留收入来源并调整方向。"
            )
            custom_timing = "现在是验证窗口，不是规模化窗口；下一次决策点应设在 14 天后。"
        else:
            core_reasons = [
                f"{hexagram_context.hexagram_name}提示应先验证关键前提，再扩大不可逆投入。",
                "当前信息尚不足以支持一次性、不可逆的选择。",
                "优先选择能产生新证据且保留退路的行动。",
            ]
            option_comparison = [
                {"option": "立即推进", "benefit": "行动快", "cost_or_risk": "信息不足时返工成本高"},
                {"option": "小范围试点", "benefit": "获得真实反馈并保留退路", "cost_or_risk": "短期速度较慢"},
                {"option": "暂缓", "benefit": "避免过早承诺", "cost_or_risk": "可能错过窗口"},
            ]
            decision_conditions = ["明确目标、预算、期限和成功标准。", "先完成一个可逆的小规模验证。"]
            stop_conditions = ["成本超过预设上限。", "关键前提被真实证据否定。"]
            missing_information = ["备选方案及机会成本", "可承受的最大损失", "明确的复评期限"]
            review_trigger = "完成第一轮小规模验证或关键外部条件变化时复评"

        populated = sum(
            bool(value.strip())
            for value in (
                question.background,
                question.constraints,
                question.expected_outcome,
                question.time_horizon,
                question.risk_tolerance,
            )
        )
        confidence = "较高" if populated >= 4 and len(question.raw_question) >= 20 else "中"
        result = {
            "decision_tendency": tendency,
            "core_reasons": core_reasons,
            "option_comparison": option_comparison,
            "decision_conditions": decision_conditions,
            "stop_conditions": stop_conditions,
            "missing_information": missing_information,
            "review_trigger": review_trigger,
            "confidence": confidence,
        }
        if custom_overall:
            result["_overall_advice"] = custom_overall
        if custom_timing:
            result["_timing_judgment"] = custom_timing
        return result

    def _generate_mock_report_data(
        self,
        question: QuestionContext,
        hexagram_context: HexagramContext,
        yao_analyses: list[YaoAnalysis],
    ) -> tuple[str, str, str, list[str]]:
        hexagram_name = hexagram_context.hexagram_name
        hexagram_id = hexagram_context.hexagram_id

        yao_highlights = [
            _strip_sentence_end(ya.advice) for ya in yao_analyses if ya.advice
        ][:3]
        if not yao_highlights:
            yao_highlights = ["审慎行事", "把握时机", "注重积累"]

        overall_advice = (
            f"根据{hexagram_name}（第{hexagram_id}卦）的启示，建议您："
            + "。".join(yao_highlights)
            + "。易经强调因时而动，顺势而为。"
        )

        risks = [
            _strip_sentence_end(ya.risks)
            for ya in yao_analyses
            if ya.risks and ya.risks != "待评估"
        ][:2]
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
    ) -> dict[str, Any]:
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

请基于以上六爻分析，生成能直接支持行动的决策参考报告。
必须区分用户已提供的事实与系统推断；信息不足时应明确列出，不得自行补造事实。

必须严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "overall_advice": "综合六爻解读，给出整体建议（2-3句话）",
  "key_risks": "提炼主要风险点，用分号分隔",
  "timing_judgment": "分析当前行动时机（1-2句话）",
  "next_steps": ["7天内可执行的步骤1", "步骤2", "步骤3"],
  "decision_tendency": "推进/有条件推进/暂缓/停止 四选一",
  "core_reasons": ["理由1", "理由2", "理由3"],
  "option_comparison": [
    {{"option": "选项", "benefit": "收益", "cost_or_risk": "成本或风险"}}
  ],
  "decision_conditions": ["满足后才推进的条件"],
  "stop_conditions": ["出现后应停止或调整的条件"],
  "missing_information": ["仍需确认且可能改变结论的信息"],
  "review_trigger": "明确复评日期或事件",
  "confidence": "低/中/较高"
}}"""

        try:
            assert self._llm_call is not None, "LLM call should not be None"
            response = self._llm_call(
                "你是决策报告官，负责综合六爻分析生成结构化的决策参考报告。",
                user_prompt,
            )
            logger.info("LLM call succeeded, parsing response...")
            overall_advice, key_risks, timing_judgment, next_steps = (
                self._parse_llm_response(response)
            )
            result: dict[str, Any] = {
                "overall_advice": overall_advice,
                "key_risks": key_risks,
                "timing_judgment": timing_judgment,
                "next_steps": next_steps,
            }
            result.update(
                self._build_decision_v2(
                    question,
                    hexagram_context,
                    yao_analyses,
                    overall_advice,
                    key_risks,
                    timing_judgment,
                    next_steps,
                )
            )
            result.pop("_overall_advice", None)
            result.pop("_timing_judgment", None)

            json_str = self._extract_json_object(self._filter_think_content(response))
            if json_str:
                try:
                    payload = json.loads(json_str)
                    list_fields = (
                        "core_reasons",
                        "option_comparison",
                        "decision_conditions",
                        "stop_conditions",
                        "missing_information",
                    )
                    for field_name in list_fields:
                        value = payload.get(field_name)
                        if isinstance(value, list) and value:
                            result[field_name] = value
                    for field_name in (
                        "decision_tendency",
                        "review_trigger",
                        "confidence",
                    ):
                        value = payload.get(field_name)
                        if isinstance(value, str) and value.strip():
                            result[field_name] = value.strip()
                except json.JSONDecodeError:
                    pass
            return result
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            logger.warning("Falling back to mock report generation")
            overall_advice, key_risks, timing_judgment, next_steps = (
                self._generate_mock_report_data(
                    question, hexagram_context, yao_analyses
                )
            )
            decision_data = self._build_decision_v2(
                question,
                hexagram_context,
                yao_analyses,
                overall_advice,
                key_risks,
                timing_judgment,
                next_steps,
            )
            overall_advice = decision_data.pop("_overall_advice", overall_advice)
            timing_judgment = decision_data.pop(
                "_timing_judgment", timing_judgment
            )
            return {
                "overall_advice": overall_advice,
                "key_risks": key_risks,
                "timing_judgment": timing_judgment,
                "next_steps": next_steps,
                **decision_data,
            }

    def _parse_llm_response(self, response: str) -> tuple[str, str, str, list[str]]:
        """Parse LLM response into report components."""
        response = self._filter_think_content(response)

        json_result = self._try_parse_json(response)
        if json_result:
            return json_result

        return self._parse_text_response(response)

    def _filter_think_content(self, response: str) -> str:
        """Remove think/reasoning blocks from response."""
        return filter_think_content(response)

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
            f"## 决策倾向",
            f"**{report.decision_tendency}**（置信度：{report.confidence}）",
            f"",
            f"## 核心理由",
        ]
        for reason in report.core_reasons:
            lines.append(f"- {reason}")
        lines.extend(
            [
            f"",
            f"## 六爻分析",
            ]
        )

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

        if report.decision_conditions:
            lines.extend(["", "## 推进条件"])
            lines.extend(f"- {item}" for item in report.decision_conditions)
        if report.stop_conditions:
            lines.extend(["", "## 停止条件"])
            lines.extend(f"- {item}" for item in report.stop_conditions)
        if report.missing_information:
            lines.extend(["", "## 仍需确认的信息"])
            lines.extend(f"- {item}" for item in report.missing_information)
        lines.extend(["", "## 复评触发点", report.review_trigger])

        return "\n".join(lines)
