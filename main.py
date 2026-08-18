#!/usr/bin/env python3
"""
易策 (yice) - AI multi-agent decision system CLI entry point.

Usage:
    python main.py              # Start interactive session
    python main.py --help       # Show help
    python main.py --version    # Show version
"""

import json
import logging
import os
import sys
from typing import Callable, Optional

# Python version check
MIN_PYTHON_VERSION = (3, 11)
if sys.version_info < MIN_PYTHON_VERSION:
    print(f"❌ 需要 Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+")
    print(f"   当前版本: {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)

from core.data_loader import DataLoader, DataLoaderConfig
from core.errors import DataError, LLMCallError, PartialFailureError
from core.llm_client import LLMClient, LLMConfig, load_config
from core.logging_config import setup_logging
from core.models import DecisionReport, QuestionContext
from core.config_validator import ConfigValidator
from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
from agents.scene_router import SceneRouter, SceneRouterConfig
from agents.yao_agents import YaoAgentOrchestrator
from agents.reporter import ReporterAgent, ReporterConfig


VERSION = "1.2.0"

# Setup logging
setup_logging(
    level="INFO",
    log_file="logs/yice.log",
    json_format=False,
    sensitive_fields=["api_key", "password", "secret", "sk-"],
    console_level="WARNING",
)
logger = logging.getLogger(__name__)


def show_help():
    """Display help message."""
    print(__doc__)
    print("\n易策是一个基于易经哲学的AI决策参考系统。")
    print("系统会根据您的问题，匹配相关卦象，并生成决策参考报告。\n")
    print("选项:")
    print("  -h, --help     显示帮助信息")
    print("  -v, --version  显示版本信息")
    print("\n交互命令:")
    print("  quit/exit/q    退出程序")


def show_version():
    """Display version information."""
    print(f"yice version {VERSION}")


def create_llm_call(client: LLMClient) -> Callable[[str, str], str]:
    """Create a callable wrapper for LLM client.

    Args:
        client: LLMClient instance.

    Returns:
        Callable that takes (system_prompt, user_prompt) and returns response.
    """

    def llm_call(system_prompt: str, user_prompt: str) -> str:
        return client.chat(system_prompt, user_prompt)

    return llm_call


def load_models_config(config_path: Optional[str] = None) -> dict:
    """Load models.json configuration with validation.

    Args:
        config_path: Optional config path. Defaults to YICE_MODELS_CONFIG
            or models.json.

    Returns:
        Configuration dictionary with providers and agents.

    Raises:
        FileNotFoundError: If models.json doesn't exist.
        ValueError: If configuration is invalid.
    """
    config_path = config_path or os.getenv("YICE_MODELS_CONFIG", "models.json")
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"配置文件 {config_path} 不存在。请复制 models.example.json 并填写API密钥。"
        )

    validator = ConfigValidator(config)
    if not validator.validate():
        raise ValueError(f"配置验证失败: {validator.errors}")

    return config


def create_llm_client(config: dict, agent_name: str) -> Optional[LLMClient]:
    """Create LLM client for a specific agent.

    Args:
        config: Full models configuration.
        agent_name: Name of the agent to get config for.

    Returns:
        LLMClient instance or None if configuration is incomplete.
    """
    agents = config.get("agents", {})
    providers = config.get("providers", {})

    agent_config = agents.get(agent_name, {})
    provider_name = agent_config.get("provider")
    model = agent_config.get("model")

    if not provider_name or not model:
        logger.warning(f"No LLM config for agent {agent_name}")
        return None

    provider_config = providers.get(provider_name, {})
    api_key = provider_config.get("api_key")
    base_url = provider_config.get("base_url", "https://api.openai.com")
    default_model = provider_config.get("default_model", model)

    if not api_key:
        logger.warning(f"No API key for provider {provider_name}")
        return None

    return LLMClient(
        LLMConfig(
            provider=provider_name,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    )


def create_agent_llm_calls(
    config: Optional[dict],
) -> dict[str, Callable[[str, str], str]]:
    """Create the independently configured callable for each pipeline role."""
    if not config:
        return {}
    calls: dict[str, Callable[[str, str], str]] = {}
    for agent_name in ("qigua_agent", "scene_router", "yao_agent", "reporter"):
        client = create_llm_client(config, agent_name)
        if client:
            calls[agent_name] = create_llm_call(client)
    return calls


def build_question_context(
    raw_question: str, llm_call: Optional[Callable[[str, str], str]]
) -> QuestionContext:
    """Build QuestionContext from raw user question.

    In MVP, uses simple heuristic extraction. In M2+, this will be
    replaced by QiguaAgent multi-turn dialogue.

    Args:
        raw_question: Raw user question string.
        llm_call: Optional LLM callable for analysis.

    Returns:
        QuestionContext with extracted fields.
    """
    # Simple question type detection
    question_type = "综合"
    type_keywords = {
        "创业": [
            "创业",
            "开公司",
            "做生意",
            "项目",
            "产品",
            "原型",
            "客户",
            "试用",
            "现金流",
            "全职投入",
        ],
        "职业": ["职业", "工作", "跳槽", "晋升", "就业"],
        "投资": ["投资", "理财", "股票", "基金", "财富"],
        "人际": ["人际", "关系", "社交", "朋友", "合作"],
        "学业": ["学业", "学习", "考试", "升学"],
        "婚恋": ["婚恋", "感情", "婚姻", "恋爱"],
        "健康": ["健康", "身体", "医疗"],
    }

    for qtype, keywords in type_keywords.items():
        if any(kw in raw_question for kw in keywords):
            question_type = qtype
            break

    # If LLM available, use it for better extraction
    if llm_call:
        try:
            prompt = f"""分析以下问题，提取关键信息（用JSON格式回复）：
问题：{raw_question}

请提取：
1. question_type: 问题类型（创业/职业/投资/人际/学业/婚恋/健康/综合）
2. background: 问题背景（简短描述）
3. expected_outcome: 期望结果

只回复JSON，格式：{{"question_type": "...", "background": "...", "expected_outcome": "..."}}"""

            response = llm_call("你是问题分析助手，擅长提取问题关键信息。", prompt)
            # Try to parse JSON from response
            if "{" in response and "}" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                question_type = data.get("question_type", question_type)
                background = data.get("background", "")
                expected_outcome = data.get("expected_outcome", "")
            else:
                background = ""
                expected_outcome = ""
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            background = ""
            expected_outcome = ""
    else:
        background = ""
        expected_outcome = ""

    return QuestionContext(
        raw_question=raw_question,
        question_type=question_type,
        background=background,
        constraints="",
        expected_outcome=expected_outcome,
        time_horizon="中期",
        risk_tolerance="中",
        is_complete=True,
    )


def run_pipeline(
    question: str,
    data_loader: DataLoader,
    llm_call: Optional[Callable[[str, str], str]],
    use_qigua: bool = True,
    agent_llm_calls: Optional[dict[str, Callable[[str, str], str]]] = None,
) -> Optional[DecisionReport]:
    """Run the full decision pipeline.

    Pipeline stages:
    1. QiguaAgent (optional) - Multi-turn dialogue for context
    2. SceneRouter - Match question to hexagram
    3. YaoAgentOrchestrator - Analyze 6 yao positions
    4. ReporterAgent - Generate final report

    Args:
        question: Raw user question.
        data_loader: DataLoader with hexagram data.
        llm_call: Optional LLM callable.
        use_qigua: Whether to use QiguaAgent for multi-turn dialogue.

    Returns:
        DecisionReport or None if pipeline fails.
    """
    try:
        calls = agent_llm_calls or {}
        qigua_llm = calls.get("qigua_agent", llm_call)
        router_llm = calls.get("scene_router", llm_call)
        yao_llm = calls.get("yao_agent", llm_call)
        reporter_llm = calls.get("reporter", llm_call)
        # Stage 1: Build question context
        if use_qigua and qigua_llm:
            print("\n[1/4] 起卦官对话中...")
            qigua_agent = QiguaAgent(QiguaAgentConfig(llm_call=qigua_llm))
            question_ctx = qigua_agent.collect_context(question)
            logger.info(f"Question type: {question_ctx.question_type}")
        else:
            print("\n[1/4] 本地问题解析中...")
            question_ctx = build_question_context(question, qigua_llm)
            logger.info(f"Question type: {question_ctx.question_type}")

        # Stage 2: Route to hexagram
        print("[2/4] 匹配卦象中...")
        router = SceneRouter(
            SceneRouterConfig(
                scene_mapping_path="data/scene_mapping.json",
                llm_call=router_llm,
                data_loader=data_loader,
            )
        )
        hexagram_ctx = router.route(question_ctx)

        print(
            f"      卦象：{hexagram_ctx.hexagram_name}（第{hexagram_ctx.hexagram_id}卦）"
        )
        print(f"      匹配方式：{hexagram_ctx.match_reason}")

        # Stage 3: Analyze 6 yao positions
        print("[3/4] 六爻分析...")
        yao_orchestrator = YaoAgentOrchestrator(llm_call=yao_llm)

        try:
            yao_analyses = yao_orchestrator.analyze_all(hexagram_ctx)
        except PartialFailureError as e:
            # Handle partial failures - continue with successful analyses
            logger.warning(
                f"Partial failure: {e.failed_positions} failed, {e.successful_positions} succeeded"
            )
            yao_analyses = [
                e.partial_results.get(pos.value)
                for pos in yao_orchestrator._agents.keys()
            ]
            yao_analyses = [ya for ya in yao_analyses if ya is not None]
            if not yao_analyses:
                print("错误：所有爻位分析失败")
                return None

        # Stage 4: Generate report
        print("[4/4] 生成报告中...")
        reporter = ReporterAgent(ReporterConfig(llm_call=reporter_llm))
        report = reporter.generate_report(question_ctx, hexagram_ctx, yao_analyses)

        return report

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        print(f"\n处理过程中出现错误：{e}")
        return None


def format_console_excerpt(text: str, max_chars: int = 120) -> str:
    """Compact long source text for interactive console output."""
    excerpt = text.split("【", 1)[0]
    excerpt = " ".join(excerpt.split())
    if len(excerpt) > max_chars:
        return excerpt[:max_chars].rstrip() + "..."
    return excerpt


def print_report(report: DecisionReport):
    """Print decision report to console.

    Args:
        report: DecisionReport to print.
    """
    print("\n" + "=" * 60)
    print("                  决 策 参 考 报 告")
    print("=" * 60)

    print(f"\n【问题】{report.question.raw_question}")
    print(
        f"\n【卦象】{report.hexagram.hexagram_name}（第{report.hexagram.hexagram_id}卦）"
    )
    print(f"\n【决策倾向】{report.decision_tendency}（置信度：{report.confidence}）")
    if report.core_reasons:
        print("\n【核心理由】")
        for reason in report.core_reasons:
            print(f"  - {reason}")

    print("\n" + "-" * 60)
    print("                    六 爻 分 析")
    print("-" * 60)

    for ya in report.yao_analyses:
        print(f"\n■ {ya.line_name}")
        print(f"  爻辞：{format_console_excerpt(ya.yao_ci)}")
        print(f"  解读：{ya.analysis}")
        print(f"  建议：{ya.advice}")
        print(f"  风险：{ya.risks}")

    if report.hu_gua_analysis:
        print("\n" + "-" * 60)
        print(report.hu_gua_analysis)

    print("\n" + "-" * 60)
    print("                    综 合 建 议")
    print("-" * 60)

    print(f"\n【综合建议】{report.overall_advice}")
    print(f"\n【关键风险】{report.key_risks}")
    print(f"\n【时机判断】{report.timing_judgment}")

    if report.decision_conditions:
        print("\n【推进条件】")
        for item in report.decision_conditions:
            print(f"  - {item}")

    if report.stop_conditions:
        print("\n【停止条件】")
        for item in report.stop_conditions:
            print(f"  - {item}")

    if report.missing_information:
        print("\n【仍需确认】")
        for item in report.missing_information:
            print(f"  - {item}")

    print(f"\n【复评触发点】{report.review_trigger}")

    print("\n【下一步行动】")
    for i, step in enumerate(report.next_steps, 1):
        print(f"  {i}. {step}")

    print("\n" + "=" * 60)
    print("注：本报告仅供参考，不构成决策建议。")
    print("=" * 60)


def main():
    """Main entry point."""
    # Handle command line arguments
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if arg in ("-h", "--help"):
            show_help()
            return 0
        elif arg in ("-v", "--version"):
            show_version()
            return 0
        else:
            print(f"错误：未知参数 '{arg}'", file=sys.stderr)
            print("使用 'python main.py --help' 查看帮助。", file=sys.stderr)
            return 1

    # Load configuration. Missing or example credentials should not block
    # first-run exploration; the CLI can run a deterministic local demo.
    models_config = None
    try:
        models_config = load_models_config()
        print("✓ 配置验证通过")
    except FileNotFoundError as e:
        print("ℹ️  未找到模型配置，已进入本地演示模式。")
        print(f"   {e}")
        print("   无需 API Key 也可以先体验完整流程。")
        print("   配置 LLM 后可获得更细致的 AI 推演：cp models.example.json models.json")
    except ValueError as e:
        print("⚠️  配置未启用，已进入本地演示模式。")
        print(f"   原因：{e}")
        print("   请把 models.json 中的示例 API Key 替换为真实 Key 后再启用 LLM。")

    agent_llm_calls = create_agent_llm_calls(models_config)
    llm_call = agent_llm_calls.get("scene_router")

    if llm_call is None:
        print("本地演示模式：使用内置卦象、爻辞和规则生成决策参考。")

    # Load data
    try:
        data_loader = DataLoader(DataLoaderConfig(data_dir="data"))
    except DataError as e:
        print("❌ 数据加载失败。")
        print("请运行以下命令生成数据：")
        print("  python3 scripts/generate_data.py")
        print(f"\n技术细节：{e}")
        return 1

    # Interactive session
    print("\n欢迎使用易策 (yice) - AI 决策参考系统")
    print("输入您的问题，系统将为您生成决策参考报告。")
    print("输入 'quit' 或 'exit' 退出。\n")

    while True:
        try:
            question = input("请输入您的问题：").strip()

            if not question:
                continue

            if question.lower() in ("quit", "exit", "q"):
                print("再见！")
                return 0

            # Run pipeline
            report = run_pipeline(
                question,
                data_loader,
                llm_call,
                use_qigua=True,
                agent_llm_calls=agent_llm_calls,
            )

            if report:
                print_report(report)
            else:
                print("\n无法生成报告，请稍后重试。")

            print()  # Blank line for readability

        except LLMCallError as e:
            print("❌ 抱歉，AI 服务调用失败。")
            print("可能原因：")
            print("  1. 网络连接问题")
            print("  2. API 配额已用完")
            print("  3. 服务暂时不可用")
            print("\n建议：")
            print("  - 检查网络连接")
            print("  - 检查 models.json 配置")
            print("  - 稍后重试")
            print(f"\n技术细节：{e}")
        except DataError as e:
            print("❌ 数据加载失败。")
            print("请运行：python3 scripts/generate_data.py")
            print(f"\n技术细节：{e}")
        except KeyboardInterrupt:
            print("\n👋 已取消操作。")
            return 130
        except EOFError:
            print("\n再见！")
            return 0
        except Exception as e:
            print(f"❌ 发生未知错误：{e}")
            print("请查看日志或提交 issue 到 GitHub")
            logger.exception("Unexpected error in main loop")


if __name__ == "__main__":
    sys.exit(main())
