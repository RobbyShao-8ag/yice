import logging
import sys
from pathlib import Path
from typing import Any, Callable, Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.data_loader import DataLoader, DataLoaderConfig
from core.llm_client import LLMClient, LLMConfig
from core.models import DecisionReport, HexagramContext, QuestionContext


logger = logging.getLogger(__name__)


class AgentBridgeService:
    """Bridge service connecting Web API to CLI agent system."""

    def __init__(self):
        self.data_loader: Optional[DataLoader] = None
        self.llm_client: Optional[LLMClient] = None
        self._initialized = False

    def initialize(self, models_config: Optional[dict[str, Any]] = None) -> None:
        """Initialize the bridge service with configuration."""
        try:
            data_dir = project_root / "data"
            self.data_loader = DataLoader(DataLoaderConfig(data_dir=str(data_dir)))
            logger.info("Data loader initialized")

            if models_config:
                providers = models_config.get("providers", {})
                if providers:
                    provider_name = list(providers.keys())[0]
                    provider = providers[provider_name]
                    self.llm_client = LLMClient(
                        LLMConfig(
                            provider=provider_name,
                            api_key=provider.get("api_key", ""),
                            base_url=provider.get("base_url", "https://api.openai.com"),
                            model=provider.get("default_model", "gpt-3.5-turbo"),
                        )
                    )
                    logger.info(f"LLM client initialized for provider: {provider_name}")

            self._initialized = True
            logger.info("AgentBridgeService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AgentBridgeService: {e}")
            self._initialized = False

    def create_llm_call(self) -> Optional[Callable[[str, str], str]]:
        """Create LLM callable wrapper."""
        if not self.llm_client:
            return None

        def llm_call(system_prompt: str, user_prompt: str) -> str:
            return self.llm_client.chat(system_prompt, user_prompt)

        return llm_call

    async def run_decision_pipeline(
        self,
        question: str,
        websocket_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> Optional[DecisionReport]:
        """Run the full decision pipeline.

        Args:
            question: User question string.
            websocket_callback: Optional callback for progress updates.

        Returns:
            DecisionReport or None if pipeline fails.
        """
        if not self._initialized:
            logger.error("AgentBridgeService not initialized")
            return None

        try:
            from agents.qigua_agent import QiguaAgent, QiguaAgentConfig
            from agents.reporter import ReporterAgent, ReporterConfig
            from agents.scene_router import SceneRouter, SceneRouterConfig
            from agents.yao_agents import YaoAgentOrchestrator

            llm_call = self.create_llm_call()

            if websocket_callback:
                websocket_callback(
                    {
                        "stage": "qigua",
                        "status": "started",
                        "message": "起卦官对话中...",
                    }
                )

            question_ctx = QuestionContext(
                raw_question=question,
                question_type="综合",
                background="",
                constraints="",
                expected_outcome="",
                time_horizon="中期",
                risk_tolerance="中",
                is_complete=True,
            )

            if websocket_callback:
                websocket_callback(
                    {"stage": "router", "status": "started", "message": "匹配卦象中..."}
                )

            router = SceneRouter(
                SceneRouterConfig(
                    scene_mapping_path=str(
                        project_root / "data" / "scene_mapping.json"
                    ),
                    llm_call=llm_call,
                    data_loader=self.data_loader,
                )
            )
            hexagram_ctx = router.route(question_ctx)

            if websocket_callback:
                websocket_callback(
                    {
                        "stage": "router",
                        "status": "completed",
                        "hexagram": hexagram_ctx.hexagram_name,
                    }
                )

            if websocket_callback:
                websocket_callback(
                    {"stage": "yao", "status": "started", "message": "六爻分析中..."}
                )

            yao_orchestrator = YaoAgentOrchestrator(llm_call=llm_call)
            yao_analyses = yao_orchestrator.analyze_all(hexagram_ctx)

            if websocket_callback:
                websocket_callback(
                    {
                        "stage": "yao",
                        "status": "completed",
                        "analyses_count": len(yao_analyses),
                    }
                )

            if websocket_callback:
                websocket_callback(
                    {
                        "stage": "reporter",
                        "status": "started",
                        "message": "生成报告中...",
                    }
                )

            reporter = ReporterAgent(ReporterConfig(llm_call=llm_call))
            report = reporter.generate_report(question_ctx, hexagram_ctx, yao_analyses)

            if websocket_callback:
                websocket_callback(
                    {
                        "stage": "complete",
                        "status": "success",
                        "message": "报告生成完成",
                    }
                )

            return report

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            if websocket_callback:
                websocket_callback(
                    {"stage": "error", "status": "failed", "message": str(e)}
                )
            return None
