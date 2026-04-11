import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.models import QuestionContext

router = APIRouter()
logger = logging.getLogger(__name__)


def get_yao_name(position: int, binary_code: list[int]) -> str:
    """Calculate correct yao name based on position and binary code."""
    if position < 1 or position > 6:
        return f"第{position}爻"

    if not binary_code or len(binary_code) < 6:
        binary_code = [1, 1, 1, 1, 1, 1]

    is_yang = binary_code[position - 1] == 1
    numeral = "九" if is_yang else "六"

    if position == 1:
        return f"初{numeral}"
    elif position == 6:
        return f"上{numeral}"
    else:
        positions = ["二", "三", "四", "五"]
        return f"{numeral}{positions[position - 2]}"


# Load models configuration
MODELS_CONFIG_PATH = project_root / "models.json"
_models_config = None


def load_models_config() -> dict:
    """Load models configuration from models.json."""
    global _models_config
    if _models_config is None:
        try:
            with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
                _models_config = json.load(f)
            logger.info(f"Loaded models config from {MODELS_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to load models config: {e}")
            _models_config = {"providers": {}, "agents": {}}
    return _models_config


@dataclass
class DialogueSession:
    """Holds state for a single dialogue session with QiguaAgent."""

    websocket: WebSocket
    raw_question: str = ""
    dialogue_history: list[dict] = field(default_factory=list)
    extra_context: dict = field(default_factory=dict)
    question_type: str = "综合"
    current_round: int = 0
    is_complete: bool = False
    question_context: Optional[QuestionContext] = None
    # For tracking last question info
    last_question: str = ""
    last_options: list[str] = field(default_factory=list)
    last_field: str = ""


class ConnectionManager:
    """WebSocket connection manager."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.sessions: dict[WebSocket, DialogueSession] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.sessions[websocket] = DialogueSession(websocket=websocket)
        logger.info(f"WebSocket connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.sessions:
            del self.sessions[websocket]
        logger.info(f"WebSocket disconnected: {websocket.client}")

    def get_session(self, websocket: WebSocket) -> Optional[DialogueSession]:
        """Get dialogue session for a websocket connection."""
        return self.sessions.get(websocket)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast message to all connected clients."""
        if self.active_connections:
            data = json.dumps(message, ensure_ascii=False)
            for connection in self.active_connections:
                await connection.send_text(data)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]):
        """Send message to a specific client."""
        data = json.dumps(message, ensure_ascii=False)
        await websocket.send_text(data)


manager = ConnectionManager()


def parse_answer(answer: str, options: list[str]) -> str:
    """解析用户答案，返回纯文本

    支持:
    - A/a/1 -> 选项 A 的完整文本
    - B/b/2 -> 选项 B 的完整文本
    - C/c/3 -> 选项 C 的完整文本
    - D/d/4 -> 选项 D 的完整文本
    - 其他 -> 直接使用用户输入
    """
    answer = answer.strip()

    if not options:
        return answer

    upper_answer = answer.upper()

    # Try matching letter options (A, B, C, D)
    if upper_answer in ("A", "B", "C", "D"):
        for opt in options:
            if opt.startswith(upper_answer + ".") or opt.startswith(
                upper_answer + "、"
            ):
                # Return the text after the prefix
                return opt.split(".", 1)[-1].split("、", 1)[-1].strip()

    # Try matching number options (1, 2, 3, 4)
    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(options):
            opt = options[idx]
            return opt.split(".", 1)[-1].split("、", 1)[-1].strip()

    # Try matching the option text directly
    for opt in options:
        clean_opt = opt.split(".", 1)[-1].split("、", 1)[-1].strip()
        if answer == clean_opt or answer.startswith(clean_opt):
            return clean_opt

    # No match, return original answer
    return answer


async def stream_text(
    websocket: WebSocket, text: str, message_type: str = "assistant_chunk"
):
    """Stream text character by character for typing effect."""
    # For MVP, send full text at once (can be enhanced for true streaming)
    await manager.send_personal(
        websocket,
        {"type": message_type, "content": text},
    )


async def _check_sufficiency_async(
    agent: Any,
    raw_question: str,
    dialogue_history: list[dict],
    extra_context: dict,
    question_type: str,
) -> tuple[bool, list[str], str]:
    """检查信息是否充分（异步包装）

    Args:
        agent: QiguaAgent instance
        raw_question: User's original question
        dialogue_history: List of previous dialogue entries
        extra_context: Additional context collected so far
        question_type: Type of question

    Returns:
        Tuple of (is_sufficient, missing_info, reasoning)
    """
    try:
        from core.models import QuestionContext
        from agents.sufficiency_checker import SufficiencyChecker

        # Build QuestionContext
        ctx = QuestionContext(
            raw_question=raw_question,
            question_type=question_type,
            background=extra_context.get("background", ""),
            constraints=extra_context.get("constraints", ""),
            expected_outcome=extra_context.get("expected_outcome", ""),
            time_horizon=extra_context.get("time_horizon", ""),
            risk_tolerance=extra_context.get("risk_tolerance", ""),
            is_complete=False,
            dialogue_history=dialogue_history,
            extra_context=extra_context,
        )

        # Get LLM call
        llm_call = None
        if hasattr(agent, "_llm_call"):
            llm_call = agent._llm_call

        if llm_call:
            checker = SufficiencyChecker(llm_call)
            # Run blocking LLM call in thread pool with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(checker.check, ctx), timeout=10.0
                )
                return result.is_sufficient, result.missing_info, result.reasoning
            except asyncio.TimeoutError:
                logger.warning("Sufficiency check timed out, using fallback")
                # Fallback: need at least 2 rounds
                is_sufficient = len(dialogue_history) >= 3
                return bool(is_sufficient), [], "检查超时，使用默认模式"
        else:
            # Fallback: need at least 2 rounds and have background
            bg = extra_context.get("background")
            outcome = extra_context.get("expected_outcome")
            is_sufficient = len(dialogue_history) >= 2 and bg and outcome
            return bool(is_sufficient), [], "默认检查模式"

    except Exception as e:
        logger.error(f"Error in sufficiency check: {e}")
        # Default to not sufficient on error
        return False, ["检查出错"], f"检查过程出错: {e}"


async def _generate_next_question_async(
    agent: Any,
    raw_question: str,
    dialogue_history: list[dict],
    extra_context: dict,
    question_type: str,
) -> tuple[str, list[str]]:
    """Generate next question using QiguaAgent or fallback.

    For the first question (empty dialogue_history), use QuestionAnalyzer.analyze().
    For subsequent questions, use QiguaAgent._generate_next_question().

    Args:
        agent: QiguaAgent instance
        raw_question: User's original question
        dialogue_history: List of previous dialogue entries
        extra_context: Additional context collected so far
        question_type: Type of question

    Returns:
        Tuple of (question_text, options_list)
    """
    try:
        # First question - use QuestionAnalyzer.analyze() to generate dynamic question
        if len(dialogue_history) == 0:
            if hasattr(agent, "analyzer") and agent.analyzer:
                try:
                    analysis, first_question = agent.analyzer.analyze(raw_question)
                    # Clean up options (remove prefixes like "A. ")
                    cleaned_options = [
                        opt[3:].strip()
                        if len(opt) > 2 and opt[1] == "." and opt[0].isalpha()
                        else opt
                        for opt in first_question.options
                    ]
                    return first_question.question_text, cleaned_options
                except Exception as e:
                    logger.warning(
                        f"QuestionAnalyzer.analyze() failed: {e}, using fallback"
                    )
            # Fallback if analyzer not available
            return f'关于"{raw_question[:50]}..."，请描述一下目前的背景情况？', [
                "详细说明",
                "简单补充",
                "其他",
            ]

        # Subsequent questions - use QiguaAgent._generate_next_question()
        if hasattr(agent, "_generate_next_question"):
            next_question, options = agent._generate_next_question(
                question_type, extra_context, dialogue_history
            )
            # Clean up options
            cleaned_options = [
                opt[3:].strip()
                if len(opt) > 2 and opt[1] == "." and opt[0].isalpha()
                else opt
                for opt in options
            ]
            # Use fallback if LLM returned empty or default
            if not next_question or next_question == "请补充更多信息":
                return "还有其他需要补充的信息吗？", ["详细说明", "简单补充", "其他"]
            return next_question, cleaned_options

        # Final fallback
        return "还有其他需要补充的信息吗？", ["详细说明", "简单补充", "其他"]

    except Exception as e:
        logger.error(f"Error in _generate_next_question_async: {e}")
        return _get_fallback_question(len(dialogue_history))


def _get_fallback_question(round_num: int) -> tuple[str, list[str]]:
    """Fallback questions when LLM is not available."""
    questions = [
        (
            "您能描述一下目前所处的环境状态吗？",
            ["稳定期", "转型期", "起步阶段", "其他"],
        ),
        (
            "您目前拥有哪些关键资源？比如人脉、资金、技能等。",
            ["资源丰富", "中等水平", "资源有限", "不确定"],
        ),
        (
            "您期望达到什么样的目标或结果？",
            ["明确目标", "大致方向", "探索可能性", "其他"],
        ),
        (
            "您希望什么时候看到结果？",
            ["短期（3 个月内）", "中期（3-12 个月）", "长期（1 年以上）"],
        ),
        ("您能承受多大的风险？", ["保守型", "稳健型", "进取型"]),
        ("还有其他需要补充的信息吗？", ["没有了", "还有一点", "详细说明"]),
    ]
    idx = min(round_num - 1, len(questions) - 1)
    return questions[idx]


async def websocket_progress_callback(
    websocket: WebSocket, stage: str, status: str, **kwargs
):
    """Send progress updates to WebSocket client during divination pipeline."""
    message = {"stage": stage, "status": status, **kwargs}
    await manager.send_personal(websocket, message)


@router.websocket("/agent")
async def websocket_agent(websocket: WebSocket):
    """WebSocket endpoint for agent dialogue streaming (起卦对话).

    Message flow:
    - Client → Server: {"type": "user_message", "content": "我想辞职创业"}
    - Server → Client: {"type": "assistant_chunk", "content": "你目前"}
    - Server → Client: {"type": "assistant_chunk", "content": "在职还是"}
    - Server → Client: {"type": "assistant_complete", "options": ["在职", "已离职", "其他"]}

    Multi-turn dialogue with QiguaAgent:
    - Round 1: User sends initial question
    - Server: Analyzes question, generates first question + options
    - Round 2-6: User responds, server generates next question
    - After 6 rounds or sufficient info: Returns QuestionContext complete
    """
    await manager.connect(websocket)
    session = manager.get_session(websocket)

    if not session:
        logger.error("Failed to create dialogue session")
        await manager.send_personal(
            websocket, {"type": "error", "message": "无法创建对话会话"}
        )
        return

    try:
        while not session.is_complete:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "user_message":
                content = message.get("content", "")
                logger.info(f"Agent message received: {content[:50]}...")

                # First message - store as raw question
                if session.current_round == 0:
                    session.raw_question = content

                    # 添加初始问题到对话历史
                    session.dialogue_history.append(
                        {
                            "round": 0,
                            "question": "用户初始问题",
                            "answer": content,
                            "answer_text": content,
                            "field": "initial_question",
                        }
                    )

                    logger.info(f"Dialogue started with question: {content[:100]}")

                    # Initialize agent and llm_call for first question generation
                    agent = None
                    llm_call = None
                    try:
                        from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
                        from services.agent_bridge import AgentBridgeService

                        # Get LLM call from bridge with config
                        bridge = AgentBridgeService()
                        models_config = load_models_config()
                        bridge.initialize(models_config)
                        llm_call = bridge.create_llm_call()

                        if llm_call:
                            agent = QiguaAgent(
                                QiguaAgentConfig(llm_call=llm_call, max_rounds=6)
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize agent for first question: {e}"
                        )

                    # Generate first question using QuestionAnalyzer.analyze()
                    try:
                        if agent and hasattr(agent, "analyzer") and agent.analyzer:
                            analysis, first_question = agent.analyzer.analyze(
                                session.raw_question
                            )
                            session.question_type = analysis.question_type
                            # Clean up options (remove prefixes like "A. ")
                            cleaned_options = [
                                opt[3:].strip()
                                if len(opt) > 2 and opt[1] == "." and opt[0].isalpha()
                                else opt
                                for opt in first_question.options
                            ]
                            first_q_text = first_question.question_text
                            first_options = cleaned_options
                            first_field = first_question.field
                            # Save first question info to session
                            session.last_question = first_q_text
                            session.last_options = first_options
                            session.last_field = first_field
                            logger.info(
                                f"Generated first question via QuestionAnalyzer: {first_q_text[:50]}..."
                            )

                            # DEBUG: Log first question details
                            logger.info(f"[DEBUG] First question field: {first_field}")
                            logger.info(
                                f"[DEBUG] Question type: {session.question_type}"
                            )
                        else:
                            # Fallback if analyzer not available
                            first_q_text = f'关于"{session.raw_question[:50]}..."，请描述一下目前的背景情况？'
                            first_options = ["详细说明", "简单补充", "其他"]
                            first_field = "background"
                            session.last_question = first_q_text
                            session.last_options = first_options
                            session.last_field = first_field
                    except Exception as e:
                        logger.warning(
                            f"QuestionAnalyzer.analyze() failed: {e}, using fallback"
                        )
                        first_q_text = f'关于"{session.raw_question[:50]}..."，请描述一下目前的背景情况？'
                        first_options = ["详细说明", "简单补充", "其他"]
                        first_field = "background"
                        session.last_question = first_q_text
                        session.last_options = first_options
                        session.last_field = first_field

                    # Stream the first question
                    await stream_text(websocket, first_q_text, "assistant_chunk")
                    await asyncio.sleep(0.2)
                    await manager.send_personal(
                        websocket,
                        {"type": "assistant_complete", "options": first_options},
                    )
                    # Increment round after generating first question
                    session.current_round = 1
                    continue  # Skip the rest of the loop, wait for user's answer

                # Store user's answer (for round 2+)
                session.dialogue_history.append(
                    {
                        "round": session.current_round + 1,
                        "question": session.last_question,
                        "options": session.last_options,
                        "answer": content,
                        "answer_text": parse_answer(content, session.last_options),
                        "field": session.last_field,
                    }
                )
                session.current_round += 1

                # Update extra_context with the parsed answer
                answer_text = parse_answer(content, session.last_options)
                if session.last_field:
                    session.extra_context[session.last_field] = answer_text

                # DEBUG: Log context after storing user answer
                logger.info(
                    f"[DEBUG] Round {session.current_round}: extra_context = {session.extra_context}"
                )
                logger.info(
                    f"[DEBUG] Round {session.current_round}: dialogue_history length = {len(session.dialogue_history)}"
                )

                # Initialize agent and llm_call for sufficiency check
                agent = None
                llm_call = None
                try:
                    from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
                    from services.agent_bridge import AgentBridgeService

                    # Get LLM call from bridge with config
                    bridge = AgentBridgeService()
                    models_config = load_models_config()
                    bridge.initialize(models_config)
                    llm_call = bridge.create_llm_call()

                    if llm_call:
                        agent = QiguaAgent(
                            QiguaAgentConfig(llm_call=llm_call, max_rounds=6)
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize agent for sufficiency check: {e}"
                    )

                # Check if information is sufficient using SufficiencyChecker
                is_sufficient, missing_info, reasoning = await _check_sufficiency_async(
                    agent,
                    session.raw_question,
                    session.dialogue_history,
                    session.extra_context,
                    session.question_type,
                )

                if is_sufficient:
                    session.is_complete = True
                    # Build QuestionContext
                    session.question_context = QuestionContext(
                        raw_question=session.raw_question,
                        question_type=session.question_type,
                        background=session.extra_context.get("background", ""),
                        constraints=session.extra_context.get("constraints", ""),
                        expected_outcome=session.extra_context.get(
                            "expected_outcome", ""
                        ),
                        time_horizon=session.extra_context.get("time_horizon", "中期"),
                        risk_tolerance=session.extra_context.get(
                            "risk_tolerance", "中"
                        ),
                        is_complete=True,
                        dialogue_history=session.dialogue_history,
                        extra_context=session.extra_context,
                    )

                    # Send completion message
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "dialogue_complete",
                            "message": "信息收集完成，准备开始推演",
                            "question_context": {
                                "raw_question": session.raw_question,
                                "question_type": session.question_type,
                                "background": session.extra_context.get(
                                    "background", ""
                                ),
                                "constraints": session.extra_context.get(
                                    "constraints", ""
                                ),
                                "expected_outcome": session.extra_context.get(
                                    "expected_outcome", ""
                                ),
                                "time_horizon": session.extra_context.get(
                                    "time_horizon", "中期"
                                ),
                                "risk_tolerance": session.extra_context.get(
                                    "risk_tolerance", "中"
                                ),
                            },
                        },
                    )
                    break

                # Generate next question using QiguaAgent logic
                try:
                    from pathlib import Path
                    import sys

                    project_root = Path(__file__).parent.parent.parent.parent
                    sys.path.insert(0, str(project_root))

                    from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
                    from services.agent_bridge import AgentBridgeService

                    # Get LLM call from bridge with config
                    bridge = AgentBridgeService()
                    models_config = load_models_config()
                    bridge.initialize(models_config)
                    llm_call = bridge.create_llm_call()

                    if llm_call:
                        # Use QiguaAgent to generate next question
                        agent = QiguaAgent(
                            QiguaAgentConfig(llm_call=llm_call, max_rounds=6)
                        )

                        # Build temporary context for analysis
                        temp_ctx = QuestionContext(
                            raw_question=session.raw_question,
                            question_type=session.question_type,
                            background=session.extra_context.get("background", ""),
                            constraints=session.extra_context.get("constraints", ""),
                            expected_outcome=session.extra_context.get(
                                "expected_outcome", ""
                            ),
                            time_horizon=session.extra_context.get(
                                "time_horizon", "中期"
                            ),
                            risk_tolerance=session.extra_context.get(
                                "risk_tolerance", "中"
                            ),
                            is_complete=False,
                            dialogue_history=session.dialogue_history,
                            extra_context=session.extra_context,
                        )

                        # DEBUG: Log context before generating next question
                        logger.info(
                            f"[DEBUG] Generating next question with context: {session.extra_context}"
                        )
                        logger.info(
                            f"[DEBUG] Dialogue history: {len(session.dialogue_history)} entries"
                        )

                        # Generate next question dynamically
                        next_question, options = await _generate_next_question_async(
                            agent,
                            session.raw_question,
                            session.dialogue_history,
                            session.extra_context,
                            session.question_type,
                        )

                        # Stream the question character by character
                        await stream_text(websocket, next_question, "assistant_chunk")
                        await asyncio.sleep(0.2)
                        await manager.send_personal(
                            websocket,
                            {"type": "assistant_complete", "options": options},
                        )
                    else:
                        # Fallback without LLM
                        next_question, options = _get_fallback_question(
                            session.current_round
                        )
                        await stream_text(websocket, next_question, "assistant_chunk")
                        await asyncio.sleep(0.2)
                        await manager.send_personal(
                            websocket,
                            {"type": "assistant_complete", "options": options},
                        )

                except Exception as e:
                    logger.error(f"Error generating next question: {e}")
                    # Fallback on error
                    next_question, options = _get_fallback_question(
                        session.current_round
                    )
                    await stream_text(websocket, next_question, "assistant_chunk")
                    await asyncio.sleep(0.2)
                    await manager.send_personal(
                        websocket,
                        {"type": "assistant_complete", "options": options},
                    )

            elif message.get("type") == "ping":
                # Heartbeat keep-alive
                await manager.send_personal(websocket, {"type": "pong"})

            else:
                logger.warning(f"Unknown message type: {message.get('type')}")
                error_response = {
                    "type": "error",
                    "message": f"未知的消息类型：{message.get('type')}",
                }
                await manager.send_personal(websocket, error_response)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {e}")
        await manager.send_personal(
            websocket, {"type": "error", "message": "无效的 JSON 格式"}
        )
    except Exception as e:
        logger.error(f"Agent WebSocket error: {e}")
        await manager.send_personal(
            websocket, {"type": "error", "message": f"服务器错误：{str(e)}"}
        )
        manager.disconnect(websocket)


@router.websocket("/divination")
async def websocket_divination(websocket: WebSocket):
    """WebSocket endpoint for divination pipeline streaming (推演流程).

    Message flow:
    - Client → Server: {"type": "start_divination", "question_context": {...}}
    - Server → Client: {"type": "yao_start", "position": 1, "line_name": "初九"}
    - Server → Client: {"type": "yao_thinking", "position": 1, "content": "正在分析..."}
    - Server → Client: {"type": "yao_complete", "position": 1, "yao_ci": "潜龙勿用", "analysis": "..."}
    - Server → Client: {"type": "all_complete", "report": {...}}
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "start_divination":
                question_context = message.get("question_context", {})
                logger.info(
                    f"Divination started for: {question_context.get('raw_question', 'unknown')[:50]}..."
                )

                try:
                    # Import and run the decision pipeline
                    from services.agent_bridge import AgentBridgeService
                    from core.models import QuestionContext

                    # Initialize bridge service with config
                    bridge = AgentBridgeService()
                    models_config = load_models_config()
                    bridge.initialize(models_config)

                    # Convert dict to QuestionContext with defaults for missing fields
                    if isinstance(question_context, dict):
                        qc = QuestionContext(
                            raw_question=question_context.get("raw_question", ""),
                            question_type=question_context.get("question_type", "综合"),
                            background=question_context.get("background", ""),
                            constraints=question_context.get("constraints", ""),
                            expected_outcome=question_context.get(
                                "expected_outcome", ""
                            ),
                            time_horizon=question_context.get("time_horizon", "中期"),
                            risk_tolerance=question_context.get("risk_tolerance", "中"),
                        )
                    else:
                        qc = question_context

                    # Define callback for progress updates
                    async def progress_callback(update: dict[str, Any]):
                        stage = update.get("stage", "unknown")
                        status = update.get("status", "unknown")

                        if stage == "qigua":
                            await manager.send_personal(
                                websocket,
                                {
                                    "type": "stage_start",
                                    "stage": "qigua",
                                    "message": update.get("message", ""),
                                },
                            )
                        elif stage == "router":
                            if status == "started":
                                await manager.send_personal(
                                    websocket,
                                    {
                                        "type": "stage_start",
                                        "stage": "router",
                                        "message": update.get("message", ""),
                                    },
                                )
                            elif status == "completed":
                                await manager.send_personal(
                                    websocket,
                                    {
                                        "type": "hexagram_matched",
                                        "hexagram_name": update.get("hexagram", ""),
                                        "message": f"匹配卦象：{update.get('hexagram', '')}",
                                    },
                                )
                        elif stage == "yao":
                            if status == "started":
                                await manager.send_personal(
                                    websocket,
                                    {
                                        "type": "stage_start",
                                        "stage": "yao",
                                        "message": update.get("message", ""),
                                    },
                                )
                            elif status == "completed":
                                await manager.send_personal(
                                    websocket,
                                    {
                                        "type": "stage_complete",
                                        "stage": "yao",
                                        "message": "六爻分析完成",
                                    },
                                )
                        elif stage == "reporter":
                            await manager.send_personal(
                                websocket,
                                {
                                    "type": "stage_start",
                                    "stage": "reporter",
                                    "message": update.get("message", ""),
                                },
                            )
                        elif stage == "complete":
                            await manager.send_personal(
                                websocket,
                                {
                                    "type": "all_complete",
                                    "message": update.get("message", ""),
                                },
                            )
                        elif stage == "error":
                            await manager.send_personal(
                                websocket,
                                {"type": "error", "message": update.get("message", "")},
                            )

                    # Run the real divination pipeline with YaoAgents
                    await _run_yao_divination(websocket, qc, bridge)

                except Exception as e:
                    logger.error(f"Pipeline execution error: {e}")
                    await manager.send_personal(
                        websocket,
                        {"type": "error", "message": f"推演失败：{str(e)}"},
                    )

            elif message.get("type") == "ping":
                # Heartbeat keep-alive
                await manager.send_personal(websocket, {"type": "pong"})

            else:
                logger.warning(
                    f"Unknown divination message type: {message.get('type')}"
                )
                error_response = {
                    "type": "error",
                    "message": f"未知的消息类型：{message.get('type')}",
                }
                await manager.send_personal(websocket, error_response)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {e}")
        await manager.send_personal(
            websocket, {"type": "error", "message": "无效的 JSON 格式"}
        )
    except Exception as e:
        logger.error(f"Divination WebSocket error: {e}")
        await manager.send_personal(
            websocket, {"type": "error", "message": f"服务器错误：{str(e)}"}
        )
        manager.disconnect(websocket)


async def _run_yao_divination(
    websocket: WebSocket, question_ctx: QuestionContext, bridge: Any
):
    """Run real divination pipeline with YaoAgents streaming.

    Args:
        websocket: WebSocket connection for streaming
        question_ctx: QuestionContext from user dialogue
        bridge: AgentBridgeService instance with LLM configured
    """
    try:
        from pathlib import Path

        from agents.scene_router import SceneRouter, SceneRouterConfig
        from agents.yao_agents import YaoAgentOrchestrator
        from agents.reporter import ReporterAgent, ReporterConfig
        from core.models import YaoPosition, YaoAnalysis

        # Get project root
        project_root = Path(__file__).parent.parent.parent.parent

        # Send router start
        await manager.send_personal(
            websocket,
            {"type": "stage_start", "stage": "router", "message": "正在匹配卦象..."},
        )

        # Create LLM call wrapper
        llm_call = bridge.create_llm_call()

        # Scene Router - match hexagram
        router = SceneRouter(
            SceneRouterConfig(
                scene_mapping_path=str(project_root / "data" / "scene_mapping.json"),
                llm_call=llm_call,
                data_loader=bridge.data_loader,
            )
        )
        hexagram_ctx = router.route(question_ctx)

        # Send hexagram matched
        await manager.send_personal(
            websocket,
            {
                "type": "hexagram_matched",
                "hexagram_name": hexagram_ctx.hexagram_name,
                "message": f"匹配卦象：{hexagram_ctx.hexagram_name}",
            },
        )

        # Send yao start
        await manager.send_personal(
            websocket,
            {"type": "stage_start", "stage": "yao", "message": "开始六爻分析..."},
        )

        # Get lines data from hexagram_context
        hexagram_data = hexagram_ctx.hexagram_data
        lines = hexagram_data.get("lines", [])
        binary_code = hexagram_data.get("binary_code", [1, 1, 1, 1, 1, 1])

        if not lines:
            await manager.send_personal(
                websocket,
                {"type": "error", "message": "卦象数据缺失"},
            )
            return

        yao_orchestrator = YaoAgentOrchestrator(llm_call=llm_call)
        yao_analyses = []

        for i, pos in enumerate(YaoPosition):
            if i >= len(lines):
                continue

            line_data_item = lines[i]
            if not isinstance(line_data_item, dict):
                line_data_item = {
                    "line_name": get_yao_name(pos.value, binary_code),
                    "yao_ci": str(line_data_item),
                }

            correct_yao_name = get_yao_name(pos.value, binary_code)

            # Send yao start
            await manager.send_personal(
                websocket,
                {
                    "type": "yao_start",
                    "position": pos.value,
                    "line_name": correct_yao_name,
                },
            )

            # Send thinking indicator
            await manager.send_personal(
                websocket,
                {
                    "type": "yao_thinking",
                    "position": pos.value,
                    "content": f"正在分析{correct_yao_name}...",
                },
            )

            # Analyze this yao (run in thread pool to not block event loop)
            try:
                agent = yao_orchestrator.get_agent(pos)
                line_data_item["line_name"] = correct_yao_name
                yao_analysis = await asyncio.to_thread(
                    agent.analyze, hexagram_ctx, line_data_item
                )
                yao_analyses.append(yao_analysis)
            except Exception as e:
                logger.error(f"Error analyzing yao {pos.value}: {e}")
                yao_analysis = YaoAnalysis(
                    position=pos.value,
                    line_name=correct_yao_name,
                    yao_ci=line_data_item.get("yao_ci", ""),
                    analysis=f"分析出错: {str(e)}",
                    advice="请稍后重试",
                    risks="分析过程中出现错误",
                )
                yao_analyses.append(yao_analysis)

            # Send yao complete immediately after analysis
            await manager.send_personal(
                websocket,
                {
                    "type": "yao_complete",
                    "position": yao_analysis.position,
                    "line_name": correct_yao_name,
                    "yao_ci": yao_analysis.yao_ci,
                    "analysis": yao_analysis.analysis,
                    "advice": yao_analysis.advice,
                    "risks": yao_analysis.risks,
                },
            )

        # Send yao complete
        await manager.send_personal(
            websocket,
            {"type": "stage_complete", "stage": "yao", "message": "六爻分析完成"},
        )

        # Reporter - generate final report
        await manager.send_personal(
            websocket,
            {
                "type": "stage_start",
                "stage": "reporter",
                "message": "正在生成决策报告...",
            },
        )

        reporter = ReporterAgent(ReporterConfig(llm_call=llm_call))
        # Run in thread pool to not block event loop
        report = await asyncio.to_thread(
            reporter.generate_report, question_ctx, hexagram_ctx, yao_analyses
        )

        # Send final completion with report
        yao_summary = [
            {
                "position": ya.position,
                "line_name": ya.line_name,
                "yao_ci": ya.yao_ci,
                "brief": ya.analysis[:100] + "..."
                if len(ya.analysis) > 100
                else ya.analysis,
            }
            for ya in yao_analyses
        ]

        report_dict = {
            "question": {
                "raw_question": report.question.raw_question,
            },
            "overall_advice": report.overall_advice,
            "key_risks": report.key_risks,
            "timing_judgment": report.timing_judgment,
            "next_steps": report.next_steps,
            "yao_summary": yao_summary,
        }
        await manager.send_personal(
            websocket,
            {
                "type": "all_complete",
                "report": report_dict,
                "message": "推演完成",
            },
        )

    except Exception as e:
        import traceback

        logger.error(f"Yao divination error: {e}")
        logger.error(traceback.format_exc())
        await manager.send_personal(
            websocket,
            {"type": "error", "message": f"推演失败：{str(e)}"},
        )
        raise
