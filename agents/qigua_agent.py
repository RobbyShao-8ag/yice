"""
QiguaAgent V2 for the yice decision system.

起卦官 V2 - LLM 驱动的多轮对话系统。
通过智能对话收集用户问题背景，动态生成问题和选项。
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.models import QuestionContext
from agents.question_analyzer import QuestionAnalyzer
from agents.sufficiency_checker import SufficiencyChecker, SufficiencyResult
from agents.option_generator import OptionGenerator
from agents.scene_router import SceneRouter, SceneRouterConfig


@dataclass
class QiguaAgentConfig:
    """Configuration for QiguaAgent."""

    llm_call: Optional[Callable[[str, str], str]] = None
    max_rounds: int = 5


class QiguaAgent:
    """起卦官 V2 - LLM 驱动的多轮对话

    工作流程：
    1. 分析问题 - 识别类型、领域、所需信息
    2. 对话循环 - 显示问题 + 选项，收集回答
    3. 检查充分性 - LLM 判断是否足够
    4. 生成下一个问题 - 动态生成
    5. 返回完整 QuestionContext
    """

    def __init__(self, config: Optional[QiguaAgentConfig] = None):
        self._config = config or QiguaAgentConfig()
        self._llm_call = self._config.llm_call
        self._max_rounds = min(self._config.max_rounds, 5)

        if self._llm_call:
            self.analyzer = QuestionAnalyzer(self._llm_call)
            self.checker = SufficiencyChecker(self._llm_call)
            self.option_gen = OptionGenerator(self._llm_call)
            self.scene_router = SceneRouter(SceneRouterConfig(llm_call=self._llm_call))
        else:
            self.analyzer = None
            self.checker = None
            self.option_gen = None
            self.scene_router = None

    def collect_context(self, raw_question: str) -> QuestionContext:
        """通过多轮对话收集问题背景

        Args:
            raw_question: 用户原始问题

        Returns:
            QuestionContext 包含完整的背景信息
        """
        print("\n" + "=" * 50)
        print("起卦官：让我先了解一下您的情况...")
        print("=" * 50)

        dialogue_history = []
        extra_context = {}

        if not self._llm_call:
            return self._fallback_collect(raw_question)

        try:
            # Type guard: self.analyzer is not None when self._llm_call exists
            assert self.analyzer is not None
            analysis, first_question = self.analyzer.analyze(raw_question)
            question_type = analysis.question_type

            print(f"\n【问题类型】{question_type}")
            print(f"【分析领域】{analysis.domain}")

            for round_num in range(1, self._max_rounds + 1):
                print(f"\n[对话 {round_num}/{self._max_rounds}]")

                if round_num == 1:
                    current_question = first_question.question_text
                    options = first_question.options
                    current_field = first_question.field
                else:
                    current_question, options = self._generate_next_question(
                        question_type, extra_context, dialogue_history
                    )
                    current_field = self._infer_field(current_question)

                if not current_question:
                    break

                print(f"\n{current_question}")
                print("-" * 40)
                for opt in options:
                    print(f"  {opt}")
                print()

                user_input = self._get_user_input(options)
                answer_text = self._parse_user_input(options, user_input)

                dialogue_entry = {
                    "round": round_num,
                    "question": current_question,
                    "options": options,
                    "answer": user_input,
                    "answer_text": answer_text,
                }
                dialogue_history.append(dialogue_entry)

                if current_field:
                    extra_context[current_field] = answer_text

                result = self._check_sufficiency(
                    raw_question, question_type, extra_context, dialogue_history
                )

                if result.is_sufficient:
                    print("\n✓ 信息收集充分，开始占卜...")
                    break

                print(f"\n起卦官：{result.reasoning}")

        except Exception as e:
            print(f"\n对话过程出错: {e}，使用简化模式...")
            return self._fallback_collect(raw_question)

        return QuestionContext(
            raw_question=raw_question,
            question_type=question_type,
            background=extra_context.get("background", ""),
            constraints=extra_context.get("constraints", ""),
            expected_outcome=extra_context.get("expected_outcome", ""),
            time_horizon=extra_context.get("time_horizon", "中期"),
            risk_tolerance=extra_context.get("risk_tolerance", "中"),
            is_complete=True,
            extra_context=extra_context,
            dialogue_history=dialogue_history,
        )

    def _check_sufficiency(
        self,
        raw_question: str,
        question_type: str,
        extra_context: dict,
        dialogue_history: list,
    ) -> SufficiencyResult:
        """检查信息充分性 - 结合 LLM 和场景路由器双重检查

        Args:
            raw_question: 原始问题
            question_type: 问题类型
            extra_context: 额外上下文
            dialogue_history: 对话历史

        Returns:
            SufficiencyResult: 充分性检查结果
        """
        ctx = QuestionContext(
            raw_question=raw_question,
            question_type=question_type,
            background=extra_context.get("background", ""),
            constraints=extra_context.get("constraints", ""),
            expected_outcome=extra_context.get("expected_outcome", ""),
            time_horizon=extra_context.get("time_horizon", ""),
            risk_tolerance=extra_context.get("risk_tolerance", ""),
            is_complete=False,
            extra_context=extra_context,
            dialogue_history=dialogue_history,
        )

        # 1. 首先使用 LLM 检查器检查
        llm_result: SufficiencyResult | None = None
        if self.checker:
            llm_result = self.checker.check(ctx)
            if not llm_result.is_sufficient:
                return llm_result

        # 2. 然后使用场景路由器检查（领域专家视角）
        if self.scene_router:
            router_result = self.scene_router.check_info_sufficiency(ctx)
            if not router_result.is_sufficient:
                # 合并两个检查器的结果
                combined_missing = (
                    list(set(llm_result.missing_info + router_result.missing_info))
                    if llm_result
                    else router_result.missing_info
                )
                reasoning_parts = []
                if llm_result:
                    reasoning_parts.append(llm_result.reasoning)
                reasoning_parts.append(router_result.reasoning)
                return SufficiencyResult(
                    is_sufficient=False,
                    missing_info=combined_missing,
                    reasoning=" | ".join(reasoning_parts),
                )

        # 两者都认为充分
        if llm_result:
            return SufficiencyResult(
                is_sufficient=True,
                missing_info=[],
                reasoning=f"{llm_result.reasoning} (场景路由器确认)",
            )
        else:
            return SufficiencyResult(
                is_sufficient=len(dialogue_history) >= 3,
                missing_info=[],
                reasoning="默认模式",
            )

    def _generate_next_question(
        self,
        question_type: str,
        extra_context: dict,
        dialogue_history: list,
    ) -> tuple[str, list[str]]:
        """生成下一个问题

        Args:
            question_type: 问题类型
            extra_context: 已收集的上下文
            dialogue_history: 对话历史

        Returns:
            tuple[问题文本, 选项列表]
        """
        context_for_llm = {}
        for entry in dialogue_history:
            field_name = entry.get("field", "")
            if field_name:
                context_for_llm[field_name] = entry.get("answer_text", "")

        context_for_llm.update(extra_context)

        if self.option_gen:
            prompt = self._build_next_question_prompt(
                question_type, context_for_llm, dialogue_history
            )
            try:
                response = self._llm_call("你是易经占卜系统的问题生成专家", prompt)
                return self._parse_next_question(response)
            except Exception:
                pass

        return self._default_next_question(len(dialogue_history)), [
            "A. 详细说明",
            "B. 简单补充",
            "C. 暂时没有",
            "D. 其他（请补充）",
        ]

    def _build_next_question_prompt(
        self, question_type: str, context: dict, history: list
    ) -> str:
        """构建下一个问题的提示词"""
        history_text = "\n".join(
            [
                f"轮次 {h.get('round', '?')}: {h.get('question', '')} -> {h.get('answer_text', '')}"
                for h in history
            ]
        )
        
        # 获取用户上一轮回答
        last_answer = history[-1].get('answer_text', '') if history else ''
        last_question = history[-1].get('question', '') if history else ''

        return f"""问题类型：{question_type}

已收集的信息:
{json_dumps(context, ensure_ascii=False)}

对话历史:
{history_text}

用户刚才回答了：{last_answer} (问题：{last_question})

基于用户的回答，请生成下一个**相关**的问题来收集更多信息。
问题应该基于用户刚才的回答内容进行追问，而不是通用的模板问题。
确保问题与上下文连贯，针对用户提供的具体信息进行深入询问。

返回 JSON 格式：
{{
    "question": "问题文本",
    "options": ["A. 选项 1", "B. 选项 2", "C. 选项 3", "D. 其他（请补充）"]
}}"""


    def _parse_next_question(self, response: str) -> tuple[str, list[str]]:
        """解析下一个问题响应"""
        import json

        json_str = self._extract_json(response)
        try:
            data = json.loads(json_str)
            question = data.get("question", "")
            options = data.get("options", [])
            if options:
                return question, options
        except Exception:
            pass

        return "请补充更多信息", ["A. 好的", "B. 知道了", "C. 继续", "D. 其他"]

    def _default_next_question(self, round_num: int) -> str:
        """默认的下一个问题"""
        questions = [
            "您对这个问题还有哪些具体的考虑？",
            "您希望什么时候看到结果？",
            "您能承受多大的风险？",
            "还有其他需要补充的吗？",
        ]
        idx = min(round_num - 1, len(questions) - 1)
        return questions[idx]

    def _infer_field(self, question: str) -> str:
        """从问题文本推断字段名"""
        q = question.lower()
        if any(kw in q for kw in ["背景", "情况", "现状", "描述"]):
            return "background"
        elif any(kw in q for kw in ["约束", "限制", "条件", "要求"]):
            return "constraints"
        elif any(kw in q for kw in ["目标", "期望", "希望", "达到"]):
            return "expected_outcome"
        elif any(kw in q for kw in ["时间", "期限", "多久"]):
            return "time_horizon"
        elif any(kw in q for kw in ["风险", "承受", "保守", "激进"]):
            return "risk_tolerance"
        return f"info_{len(self._config.__dict__)}"

    def _get_user_input(self, options: list[str]) -> str:
        """获取用户输入"""
        while True:
            try:
                user_input = input("您的选择或回答: ").strip()
                if user_input:
                    return user_input
                print("请输入您的回答")
            except KeyboardInterrupt:
                print("\n已取消")
                return "D"

    def _parse_user_input(self, options: list[str], user_input: str) -> str:
        """解析用户输入

        支持：
        - A/a/1 -> 选项 A 的完整文本
        - B/b/2 -> 选项 B 的完整文本
        - C/c/3 -> 选项 C 的完整文本
        - D/d/4 -> 选项 D 的完整文本
        - 其他 -> 直接使用用户输入
        """
        user_input = user_input.strip()

        if not options:
            return user_input

        upper_input = user_input.upper()

        if upper_input in ("A", "B", "C", "D"):
            for opt in options:
                if opt.startswith(upper_input + ".") or opt.startswith(
                    upper_input + "、"
                ):
                    return opt.split(".", 1)[-1].split("、", 1)[-1].strip()

        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(options):
                return options[idx].split(".", 1)[-1].split("、", 1)[-1].strip()

        return user_input

    def _extract_json(self, response: str) -> str:
        """从响应中提取 JSON"""
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

    def _fallback_collect(self, raw_question: str) -> QuestionContext:
        """简化模式收集（无 LLM 时）"""
        print("\n[简化模式] 请描述您的问题背景：")
        background = input("> ").strip()

        print("\n请说明您的期望目标：")
        expected = input("> ").strip()

        print("\n请说明时间范围（短期/中期/长期）：")
        time_horizon = input("> ").strip() or "中期"

        print("\n请说明风险承受能力（低/中/高）：")
        risk = input("> ").strip() or "中"

        return QuestionContext(
            raw_question=raw_question,
            question_type="综合决策",
            background=background,
            constraints="",
            expected_outcome=expected,
            time_horizon=time_horizon,
            risk_tolerance=risk,
            is_complete=True,
        )


def json_dumps(obj, ensure_ascii=True, indent=None):
    """Simple JSON dump helper"""
    import json

    return json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent)
