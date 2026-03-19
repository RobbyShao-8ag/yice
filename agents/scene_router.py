"""
SceneRouter for the yice decision system.

Routes questions to hexagrams using a 3-layer fallback strategy:
1. Exact match - scene_key directly matches scene_mapping.json
2. Fuzzy search - keyword matching and similarity search
3. LLM fallback - call LLM to analyze and recommend hexagram_id
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.models import HexagramContext, QuestionContext
from agents.sufficiency_checker import SufficiencyResult
from core.data_loader import DataLoader, DataLoaderConfig

logger = logging.getLogger(__name__)


# Default scene mapping (used when JSON file is not available)
DEFAULT_SCENE_MAPPING = {
    "创业": {
        "hexagram_id": 5,
        "hexagram_name": "需卦",
        "keywords": ["创业", "起步", "新项目"],
    },
    "职业选择": {
        "hexagram_id": 26,
        "hexagram_name": "大畜卦",
        "keywords": ["职业", "工作", "就业"],
    },
    "投资": {
        "hexagram_id": 14,
        "hexagram_name": "大有卦",
        "keywords": ["投资", "理财", "财富"],
    },
    "人际关系": {
        "hexagram_id": 19,
        "hexagram_name": "临卦",
        "keywords": ["人际", "关系", "社交"],
    },
    "学业": {
        "hexagram_id": 4,
        "hexagram_name": "蒙卦",
        "keywords": ["学业", "学习", "考试"],
    },
    "搬家": {
        "hexagram_id": 16,
        "hexagram_name": "豫卦",
        "keywords": ["搬家", "迁居", "搬迁"],
    },
    "婚恋": {
        "hexagram_id": 44,
        "hexagram_name": "姤卦",
        "keywords": ["婚恋", "感情", "婚姻"],
    },
    "健康": {
        "hexagram_id": 35,
        "hexagram_name": "晋卦",
        "keywords": ["健康", "身体", "医疗"],
    },
}

# Fallback hexagram when all strategies fail
FALLBACK_HEXAGRAM = {
    "hexagram_id": 1,
    "hexagram_name": "乾为天",
    "match_reason": "默认推荐",
}


@dataclass
class SceneRouterConfig:
    """Configuration for SceneRouter."""

    scene_mapping_path: Optional[str] = None
    llm_call: Optional[Callable[[str, str], str]] = None
    fuzzy_threshold: float = 0.3
    data_loader: Optional[DataLoader] = None


class SceneRouter:
    """Routes questions to hexagrams using 3-layer fallback strategy.

    Pipeline position: QuestionContext -> SceneRouter -> HexagramContext
    """

    def __init__(self, config: SceneRouterConfig):
        self._config = config
        self._llm_call = config.llm_call
        self._fuzzy_threshold = config.fuzzy_threshold
        self._scene_mapping = self._load_scene_mapping()
        # Use provided DataLoader or create default one
        self._data_loader = config.data_loader
        if self._data_loader is None:
            # Try to create default DataLoader
            try:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                data_dir = os.path.join(project_root, "data")
                self._data_loader = DataLoader(DataLoaderConfig(data_dir=data_dir))
                logger.info(f"Created default DataLoader with data_dir={data_dir}")
            except Exception as e:
                logger.warning(f"Failed to create default DataLoader: {e}")

    def _load_scene_mapping(self) -> dict[str, dict[str, Any]]:
        """Load scene mapping from JSON file or use default."""
        if self._config.scene_mapping_path and os.path.exists(
            self._config.scene_mapping_path
        ):
            try:
                with open(self._config.scene_mapping_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
                    logger.info(
                        f"Loaded scene mapping from {self._config.scene_mapping_path}"
                    )
                    return mapping
            except Exception as e:
                logger.warning(f"Failed to load scene mapping: {e}, using default")

        logger.info("Using default scene mapping")
        return DEFAULT_SCENE_MAPPING.copy()

    def route(self, question: QuestionContext) -> HexagramContext:
        """Route question to hexagram using 3-layer fallback strategy.

        Args:
            question: QuestionContext from QiguaAgent.

        Returns:
            HexagramContext with matched hexagram.
        """
        logger.info(f"Routing question: {question.raw_question[:50]}...")

        # Layer 1: Exact match
        result = self._exact_match(question)
        if result:
            logger.info(f"Strategy: EXACT match - hexagram_id={result['hexagram_id']}")
            return self._build_hexagram_context(question, result, "exact")

        # Layer 2: Fuzzy search
        result = self._fuzzy_search(question)
        if result:
            logger.info(
                f"Strategy: FUZZY match - hexagram_id={result['hexagram_id']}, "
                f"score={result.get('score', 0):.2f}"
            )
            return self._build_hexagram_context(question, result, "fuzzy")

        # Layer 3: LLM fallback
        result = self._llm_fallback(question)
        if result:
            logger.info(
                f"Strategy: LLM fallback - hexagram_id={result['hexagram_id']}, "
                f"confidence={result.get('confidence', 'N/A')}"
            )
            return self._build_hexagram_context(question, result, "llm")

        # Ultimate fallback
        logger.warning("All strategies failed, using fallback hexagram")
        return self._build_hexagram_context(question, FALLBACK_HEXAGRAM, "fallback")

    def _exact_match(self, question: QuestionContext) -> Optional[dict[str, Any]]:
        """Layer 1: Try exact match with scene_key."""
        # Match against question_type
        question_type = question.question_type
        if question_type in self._scene_mapping:
            return {
                **self._scene_mapping[question_type],
                "match_reason": f"精确匹配问题类型: {question_type}",
            }

        # Match against scene keywords in question text
        question_text = question.raw_question
        for scene_key, scene_data in self._scene_mapping.items():
            if scene_key in question_text:
                return {
                    **scene_data,
                    "match_reason": f"精确匹配关键词: {scene_key}",
                }

        return None

    def _fuzzy_search(self, question: QuestionContext) -> Optional[dict[str, Any]]:
        """Layer 2: Fuzzy keyword matching and similarity search."""
        question_text = question.raw_question
        question_type = question.question_type
        background = question.background
        expected = question.expected_outcome

        # Combine all text fields for search
        full_text = f"{question_type} {question_text} {background} {expected}"

        best_match = None
        best_score = 0.0

        for scene_key, scene_data in self._scene_mapping.items():
            keywords = scene_data.get("keywords", [])
            score = 0.0

            for keyword in keywords:
                # Count keyword occurrences
                if keyword in full_text:
                    score += 1.0
                # Partial match (simple substring)
                elif any(kw in keyword for kw in full_text.split()):
                    score += 0.5
                # Character-level similarity (simple)
                else:
                    common_chars = set(keyword) & set(full_text)
                    if common_chars and len(common_chars) / len(set(keyword)) > 0.5:
                        score += 0.3

            # Normalize score
            if keywords:
                score = score / len(keywords)

            if score >= self._fuzzy_threshold and score > best_score:
                best_score = score
                best_match = {
                    **scene_data,
                    "match_reason": f"模糊匹配场景: {scene_key}",
                    "score": score,
                }

        return best_match

    def _llm_fallback(self, question: QuestionContext) -> Optional[dict[str, Any]]:
        """Layer 3: Use LLM to analyze and recommend hexagram."""
        if self._llm_call is None:
            return None

        try:
            user_prompt = (
                f"用户问题：{question.raw_question}\n"
                f"问题类型：{question.question_type}\n"
                f"背景：{question.background}\n"
                f"期望结果：{question.expected_outcome}\n"
                f"风险承受：{question.risk_tolerance}\n"
                f"时间跨度：{question.time_horizon}\n\n"
                "请根据以上信息，从以下64卦中选择最合适的卦象序号（1-64），"
                "只回复序号和简短理由。"
            )

            response = self._llm_call(
                "你是易经专家，擅长根据用户问题推荐合适的卦象。", user_prompt
            )

            # Parse hexagram_id from response
            hexagram_id = self._parse_llm_response(response)
            if hexagram_id:
                # Get hexagram info (simplified - would need full data in production)
                hexagram_name = self._get_hexagram_name(hexagram_id)
                return {
                    "hexagram_id": hexagram_id,
                    "hexagram_name": hexagram_name,
                    "match_reason": f"LLM推荐: {response[:100]}",
                    "confidence": "high" if self._llm_call else "medium",
                }

        except Exception as e:
            logger.error(f"LLM fallback failed: {e}")

        return None

    def _parse_llm_response(self, response: str) -> Optional[int]:
        """Parse hexagram_id from LLM response."""
        # Look for number at start of response
        match = re.search(r"^(\d+)", response.strip())
        if match:
            hexagram_id = int(match.group(1))
            if 1 <= hexagram_id <= 64:
                return hexagram_id

        # Try to find any number in range 1-64
        numbers = re.findall(r"\b([1-9]|[1-5]\d|64)\b", response)
        if numbers:
            return int(numbers[0])

        return None

    def _get_hexagram_name(self, hexagram_id: int) -> str:
        """Get hexagram name by ID."""
        hexagram_names = {
            1: "乾为天",
            2: "坤为地",
            3: "水雷屯",
            4: "山水蒙",
            5: "水天需",
            6: "天水讼",
            7: "地水师",
            8: "水地比",
            9: "风天小畜",
            10: "天泽履",
            11: "地天泰",
            12: "天地否",
            13: "天火同人",
            14: "火天大有",
            15: "地山谦",
            16: "雷地豫",
            17: "泽雷随",
            18: "山蛊",
            19: "地泽临",
            20: "风地观",
            21: "火雷噬嗑",
            22: "山火贲",
            23: "山地剥",
            24: "地雷复",
            25: "天雷无妄",
            26: "山天大畜",
            27: "山雷颐",
            28: "泽风大过",
            29: "坎为水",
            30: "离为火",
            31: "泽山咸",
            32: "雷风恒",
            33: "天山遁",
            34: "雷天大壮",
            35: "火地晋",
            36: "地火明夷",
            37: "风火家人",
            38: "火泽睽",
            39: "水山蹇",
            40: "雷水解",
            41: "山泽损",
            42: "风雷益",
            43: "泽天夬",
            44: "天风姤",
            45: "泽地萃",
            46: "地风升",
            47: "泽水困",
            48: "水风井",
            49: "泽火革",
            50: "火风鼎",
            51: "震为雷",
            52: "艮为山",
            53: "风山渐",
            54: "雷归妹",
            55: "雷火丰",
            56: "火山旅",
            57: "巽为风",
            58: "兑为泽",
            59: "风水涣",
            60: "水泽节",
            61: "风泽中孚",
            62: "雷山小过",
            63: "水火既济",
            64: "火水未济",
        }
        return hexagram_names.get(hexagram_id, "未知卦象")

    def check_info_sufficiency(
        self,
        ctx: QuestionContext,
    ) -> SufficiencyResult:
        """检查信息是否足够匹配卦象

        作为领域专家，从卦象匹配角度评估当前收集的信息是否足够：
        1. 检查是否能通过现有信息进行卦象匹配
        2. 检查关键信息字段是否完整
        3. 返回缺失的信息和建议的下一个问题

        Args:
            ctx: 当前的问题上下文

        Returns:
            SufficiencyResult: 充分性检查结果
        """
        logger.info("Checking info sufficiency for scene routing...")

        # 关键信息字段检查
        missing_info = []

        # 1. 检查背景信息
        if not ctx.background or len(ctx.background.strip()) < 10:
            missing_info.append("详细的背景描述")

        # 2. 检查期望目标
        if not ctx.expected_outcome or len(ctx.expected_outcome.strip()) < 5:
            missing_info.append("明确的期望目标")

        # 3. 检查问题类型识别
        if not ctx.question_type or ctx.question_type == "其他":
            # 问题类型为"其他"时，需要更多信息来识别场景
            missing_info.append("问题场景类型")

        # 4. 检查对话历史长度
        if len(ctx.dialogue_history) < 2:
            missing_info.append("更多背景细节")

        # 如果存在缺失信息，返回不足
        if missing_info:
            return SufficiencyResult(
                is_sufficient=False,
                missing_info=missing_info,
                reasoning=f"卦象匹配需要更多信息：{', '.join(missing_info)}",
                next_question=self._generate_clarifying_question(ctx, missing_info),
            )

        # 尝试进行卦象匹配（预检查）
        # 如果能成功匹配，说明信息足够
        try:
            # Layer 1: 精确匹配
            exact_match = self._exact_match(ctx)
            if exact_match:
                logger.info("Info sufficient - exact match available")
                return SufficiencyResult(
                    is_sufficient=True,
                    missing_info=[],
                    reasoning="信息足够进行精确卦象匹配",
                )

            # Layer 2: 模糊匹配
            fuzzy_match = self._fuzzy_search(ctx)
            if fuzzy_match:
                logger.info("Info sufficient - fuzzy match available")
                return SufficiencyResult(
                    is_sufficient=True,
                    missing_info=[],
                    reasoning="信息足够进行模糊卦象匹配",
                )

            # Layer 3: 如果能调用 LLM，可以使用 LLM  fallback
            if self._llm_call:
                logger.info("Info sufficient - LLM fallback available")
                return SufficiencyResult(
                    is_sufficient=True,
                    missing_info=[],
                    reasoning="信息足够，可通过 LLM 推荐卦象",
                )

            # 无法匹配且无 LLM，需要更多信息
            logger.warning("Cannot match hexagram with current info and no LLM")
            return SufficiencyResult(
                is_sufficient=False,
                missing_info=["无法匹配卦象的场景信息"],
                reasoning="当前信息无法匹配到合适的卦象，需要补充场景描述",
                next_question="请详细描述您面临的具体情况属于哪个领域（如创业、职业、投资等）",
            )

        except Exception as e:
            logger.error(f"Sufficiency check failed: {e}")
            return SufficiencyResult(
                is_sufficient=False,
                missing_info=["检查过程出错"],
                reasoning=f"卦象匹配检查失败：{e}",
            )

    def _generate_clarifying_question(
        self,
        ctx: QuestionContext,
        missing_info: list[str],
    ) -> str:
        """生成澄清问题来收集缺失的信息

        Args:
            ctx: 当前问题上下文
            missing_info: 缺失的信息列表

        Returns:
            建议的下一个问题
        """
        # 根据缺失的信息类型生成针对性的问题
        if "问题场景类型" in missing_info:
            return "您面临的问题主要属于哪个领域？比如：创业、职业选择、投资理财、人际关系、学业发展等"

        if "详细的背景描述" in missing_info:
            return "能否详细描述一下您当前面临的具体情况？包括现状、已采取的行动等"

        if "明确的期望目标" in missing_info:
            return "您希望通过这次占卜获得什么样的指导？具体的目标是什么？"

        if "更多背景细节" in missing_info:
            return "关于这个问题，还有哪些重要的背景信息需要我了解的？"

        # 默认问题
        return "请补充更多关于您问题的背景信息，以便我为您推荐合适的卦象"

    def _build_hexagram_context(
        self,
        question: QuestionContext,
        hexagram_data: dict[str, Any],
        strategy: str,
    ) -> HexagramContext:
        """Build HexagramContext from routing result."""
        hexagram_id = hexagram_data["hexagram_id"]

        # Get full hexagram data from DataLoader if available
        full_hexagram_data = hexagram_data.copy()

        if self._data_loader:
            # Get hexagram info
            hex_info = self._data_loader.get_hexagram(hexagram_id)
            if hex_info:
                full_hexagram_data.update(hex_info)

            # Get lines for this hexagram
            lines = self._data_loader.get_lines_for_hexagram(hexagram_id)
            if lines:
                # Transform lines to expected format for YaoAgentOrchestrator
                full_hexagram_data["lines"] = [
                    {
                        "line_name": line.get(
                            "yao_name", f"第{line.get('position', 1)}爻"
                        ),
                        "yao_ci": line.get("text", ""),
                        "position": line.get("position", 1),
                    }
                    for line in lines
                ]
                logger.info(f"Loaded {len(lines)} lines for hexagram {hexagram_id}")
            else:
                logger.warning(f"No lines found for hexagram {hexagram_id}")
        else:
            logger.warning("No DataLoader available, hexagram_data may be incomplete")

        return HexagramContext(
            question=question,
            hexagram_id=hexagram_id,
            hexagram_name=hexagram_data["hexagram_name"],
            match_reason=f"[{strategy.upper()}] {hexagram_data.get('match_reason', '')}",
            hexagram_data=full_hexagram_data,
        )
