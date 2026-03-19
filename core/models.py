"""
Core data models for the yice decision system.

All dataclasses follow the thick data approach - system behavior is predictable
from these structures, LLM only generates final text.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import logging
import os


logger = logging.getLogger(__name__)


class YaoPosition(Enum):
    """六爻位置枚举，对应六个分析阶段。

    融合传统易经含义与现代决策映射，形成完整的爻位角色定义。
    传统含义来源于《周易》经传，现代映射对应决策分析视角。
    """

    INITIAL = 1  # 初爻 - 基础环境层 (根本 + 环境感知)
    SECOND = 2  # 二爻 - 内部资源层 (内中馈 + 资源配置)
    THIRD = 3  # 三爻 - 行动执行层 (君子终日乾乾 + 风险评估)
    FOURTH = 4  # 四爻 - 关键转折层 (门阙 + 策略执行)
    FIFTH = 5  # 五爻 - 核心决策层 (君位 + 长期规划)
    TOP = 6  # 上爻 - 终局反思层 (亢龙有悔 + 结果复盘)

    @property
    def role(self) -> str:
        """返回该爻位的现代映射角色（向后兼容）"""
        roles = {
            1: "环境感知",
            2: "资源配置",
            3: "风险评估",
            4: "策略执行",
            5: "长期规划",
            6: "结果复盘",
        }
        return roles[self.value]

    @property
    def name_cn(self) -> str:
        """返回中文名称"""
        names = {
            1: "初爻",
            2: "二爻",
            3: "三爻",
            4: "四爻",
            5: "五爻",
            6: "上爻",
        }
        return names[self.value]

    @property
    def traditional_meaning(self) -> str:
        """返回传统含义（来源于周易经传）"""
        meanings = {
            1: "根本",  # 初爻为根本，事物之始
            2: "内中馈",  # 二爻居内卦之中，承上启下
            3: "君子终日乾乾",  # 三爻多凶，需勤勉进取
            4: "门阙",  # 四爻为门，进退之机
            5: "君位",  # 五爻为君位，主导之位
            6: "亢龙有悔",  # 上爻为终，物极必反
        }
        return meanings[self.value]

    @property
    def fused_role(self) -> str:
        """返回融合角色定义（传统含义 + 现代映射）"""
        fused = {
            1: "基础环境层",  # 根本 + 环境感知
            2: "内部资源层",  # 内中馈 + 资源配置
            3: "行动执行层",  # 君子终日乾乾 + 风险评估
            4: "关键转折层",  # 门阙 + 策略执行
            5: "核心决策层",  # 君位 + 长期规划
            6: "终局反思层",  # 亢龙有悔 + 结果复盘
        }
        return fused[self.value]

    @property
    def analysis_focus(self) -> str:
        """返回分析焦点描述"""
        focus = {
            1: "识别问题根本、环境基调",
            2: "评估内部条件、资源匹配",
            3: "行动中的风险与努力",
            4: "决策关键点、策略调整",
            5: "主导方向、长远影响",
            6: "极端情况、反思总结",
        }
        return focus[self.value]


@dataclass
class QuestionContext:
    """Context captured by QiguaAgent through multi-turn dialogue."""

    raw_question: str
    question_type: str  # 创业决策 / 职业选择 / 投资判断 / 人际关系 / 其他
    background: str
    constraints: str
    expected_outcome: str
    time_horizon: str
    risk_tolerance: str  # 低 / 中 / 高
    is_complete: bool = False  # QiguaAgent sets True when all fields populated

    # V2 fields - question-specific information
    extra_context: dict[str, str] = field(default_factory=dict)
    # Records each dialogue round: [{"round": 1, "question": "...", "options": [...], "answer": "A", "answer_text": "..."}]
    dialogue_history: list[dict] = field(default_factory=list)


@dataclass
class HexagramContext:
    """Context produced by SceneRouter after hexagram matching."""

    question: QuestionContext
    hexagram_id: int
    hexagram_name: str
    match_reason: str
    hexagram_data: dict  # Full hexagram data from data_loader
    hu_gua_id: Optional[int] = None  # 互卦ID，变卦引擎(M3)使用
    # bian_gua_trigger_conditions added in M3


@dataclass
class YaoAnalysis:
    """Analysis for a single yao position (1-6)."""

    position: int  # 1-6
    line_name: str  # 初九/九二/...
    yao_ci: str
    analysis: str  # LLM generated: interpretation for current question
    advice: str  # LLM generated: specific action advice
    risks: str  # LLM generated: risk warnings


@dataclass
class HuGuaContext:
    """互卦上下文 - 用于变卦分析(M3)"""

    original_hexagram_id: int
    hu_gua_id: int
    lower_trigram: int  # 二三四爻组成的下卦（卦ID）
    upper_trigram: int  # 三四五爻组成的上卦（卦ID）


@dataclass
class DecisionReport:
    """Final decision reference report produced by ReporterAgent."""

    question: QuestionContext
    hexagram: HexagramContext
    yao_analyses: list[YaoAnalysis]
    overall_advice: str  # LLM generated: comprehensive advice
    key_risks: str  # LLM generated: core risks
    timing_judgment: str  # LLM generated: timing assessment
    next_steps: list[str]  # LLM generated: actionable next steps
    hu_gua_analysis: Optional[str] = None  # LLM generated: hu_gua interpretation

    def to_markdown(self) -> str:
        """Export report as Markdown."""
        md = "# 决策参考报告\n\n"
        md += f"## 问题\n\n{self.question.raw_question}\n\n"

        md += "## 卦象\n\n"
        md += f"{self.hexagram.hexagram_name}（第{self.hexagram.hexagram_id}卦）\n\n"

        md += "## 六爻分析\n\n"
        for yao in self.yao_analyses:
            md += f"### {yao.line_name}\n\n"
            md += f"**分析**: {yao.analysis}\n\n"
            md += f"**建议**: {yao.advice}\n\n"
            md += f"**风险**: {yao.risks}\n\n"

        if self.hu_gua_analysis:
            md += f"## 互卦分析\n\n{self.hu_gua_analysis}\n\n"

        md += f"## 综合建议\n\n{self.overall_advice}\n\n"
        md += f"## 关键风险\n\n{self.key_risks}\n\n"
        md += f"## 时机判断\n\n{self.timing_judgment}\n\n"

        md += "## 下一步行动\n\n"
        for i, step in enumerate(self.next_steps, 1):
            md += f"{i}. {step}\n"

        md += "\n---\n\n"
        md += "*本报告由易策 (yice) AI 决策系统生成，仅供参考。*\n"

        return md

    def save_to_file(self, filepath: str):
        """Save report to file.

        Args:
            filepath: Output file path (.md, .txt supported)
        """
        # Auto-detect format from extension
        if filepath.endswith(".md"):
            content = self.to_markdown()
        elif filepath.endswith(".txt"):
            content = str(self)
        else:
            # Default to markdown
            if not filepath.endswith(".md"):
                filepath += ".md"
            content = self.to_markdown()

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Report saved to: {filepath}")
