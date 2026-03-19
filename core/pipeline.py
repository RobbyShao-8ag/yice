"""
Pipeline context management and stage validators.

PipelineContext tracks the state of the decision pipeline across stages,
enabling checkpoint/rollback for error recovery and stage validation
before proceeding to the next phase.
"""

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.models import HexagramContext, QuestionContext, YaoAnalysis


VALID_STAGES = ("init", "qigua", "scene_router", "yao_analysis", "reporter", "complete")


class ValidationError(Exception):
    """Raised when stage validation fails."""

    pass


@dataclass
class PipelineContext:
    """
    Tracks pipeline execution state across stages.

    Enables checkpoint/rollback for error recovery and provides
    accumulated context for downstream agents.
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    current_stage: str = "init"
    accumulated_outputs: dict[str, Any] = field(default_factory=dict)
    error_log: list[dict[str, Any]] = field(default_factory=list)
    _checkpoints: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def checkpoint(self) -> str:
        """
        Save current state for potential rollback.

        Returns:
            Checkpoint ID for later rollback reference.
        """
        checkpoint_data = {
            "stage": self.current_stage,
            "outputs": copy.deepcopy(self.accumulated_outputs),
            "errors": copy.deepcopy(self.error_log),
        }
        self._checkpoints.append(checkpoint_data)
        return f"cp_{len(self._checkpoints) - 1}"

    def rollback(self, checkpoint_id: str | None = None) -> bool:
        """
        Restore state from a checkpoint.

        Args:
            checkpoint_id: Specific checkpoint to restore (e.g., 'cp_0').
                          If None, restores to most recent checkpoint.

        Returns:
            True if rollback succeeded, False if no checkpoint available.
        """
        if not self._checkpoints:
            return False

        if checkpoint_id is None:
            checkpoint_data = self._checkpoints[-1]
        else:
            try:
                idx = int(checkpoint_id.replace("cp_", ""))
                checkpoint_data = self._checkpoints[idx]
            except (ValueError, IndexError):
                return False

        self.current_stage = checkpoint_data["stage"]
        self.accumulated_outputs = copy.deepcopy(checkpoint_data["outputs"])
        self.error_log = copy.deepcopy(checkpoint_data["errors"])
        return True

    def log_error(
        self, stage: str, error_type: str, message: str, details: dict | None = None
    ) -> None:
        """Record an error in the pipeline error log."""
        self.error_log.append(
            {
                "stage": stage,
                "error_type": error_type,
                "message": message,
                "details": details or {},
            }
        )

    def advance_stage(self, new_stage: str) -> bool:
        """
        Advance to the next pipeline stage.

        Args:
            new_stage: Target stage name.

        Returns:
            True if stage transition is valid.

        Raises:
            ValueError: If new_stage is not a valid stage name.
        """
        if new_stage not in VALID_STAGES:
            raise ValueError(
                f"Invalid stage: {new_stage}. Valid stages: {VALID_STAGES}"
            )
        self.current_stage = new_stage
        return True


def validate_question_context(
    context: QuestionContext | dict,
) -> tuple[bool, list[str]]:
    """
    Validate that QuestionContext has all required fields populated.

    Args:
        context: QuestionContext instance or dict representation.

    Returns:
        Tuple of (is_valid, list_of_missing_or_invalid_fields).
    """
    missing = []

    if isinstance(context, dict):
        required_fields = [
            "raw_question",
            "question_type",
            "background",
            "constraints",
            "expected_outcome",
            "time_horizon",
            "risk_tolerance",
        ]
        for field_name in required_fields:
            value = context.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field_name)
    else:
        required_attrs = [
            "raw_question",
            "question_type",
            "background",
            "constraints",
            "expected_outcome",
            "time_horizon",
            "risk_tolerance",
        ]
        for attr in required_attrs:
            value = getattr(context, attr, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(attr)

    return len(missing) == 0, missing


def validate_hexagram_context(
    context: HexagramContext | dict,
) -> tuple[bool, list[str]]:
    """
    Validate that HexagramContext has required hexagram data.

    Args:
        context: HexagramContext instance or dict representation.

    Returns:
        Tuple of (is_valid, list_of_missing_or_invalid_fields).
    """
    missing = []

    if isinstance(context, dict):
        if "hexagram_id" not in context or context["hexagram_id"] is None:
            missing.append("hexagram_id")
        if "hexagram_name" not in context or not context.get("hexagram_name"):
            missing.append("hexagram_name")
        hexagram_data = context.get("hexagram_data", {})
        if not hexagram_data or "lines" not in hexagram_data:
            missing.append("hexagram_data.lines")
    else:
        if context.hexagram_id is None:
            missing.append("hexagram_id")
        if not context.hexagram_name:
            missing.append("hexagram_name")
        if not context.hexagram_data or "lines" not in context.hexagram_data:
            missing.append("hexagram_data.lines")

    return len(missing) == 0, missing


def validate_yao_analyses(
    analyses: list[YaoAnalysis] | list[dict],
) -> tuple[bool, list[str]]:
    """
    Validate that all 6 yao position analyses are complete.

    Args:
        analyses: List of YaoAnalysis instances or dict representations.

    Returns:
        Tuple of (is_valid, list_of_missing_positions).
    """
    if not analyses:
        return False, ["all positions (empty list)"]

    if len(analyses) != 6:
        return False, [f"expected 6 analyses, got {len(analyses)}"]

    positions_found = set()
    missing_fields = []

    for i, analysis in enumerate(analyses):
        if isinstance(analysis, dict):
            pos = analysis.get("position")
            if pos is None:
                missing_fields.append(f"analysis[{i}].position")
                continue
            positions_found.add(pos)

            for field_name in ["line_name", "yao_ci", "analysis", "advice", "risks"]:
                if not analysis.get(field_name):
                    missing_fields.append(f"analysis[{i}].{field_name}")
        else:
            positions_found.add(analysis.position)
            for attr in ["line_name", "yao_ci", "analysis", "advice", "risks"]:
                value = getattr(analysis, attr, None)
                if not value:
                    missing_fields.append(f"analysis[{i}].{attr}")

    expected_positions = {1, 2, 3, 4, 5, 6}
    missing_positions = expected_positions - positions_found

    if missing_positions:
        missing_fields.extend([f"position {p}" for p in sorted(missing_positions)])

    return len(missing_fields) == 0, missing_fields


def validate_stage_transition(current: str, target: str) -> bool:
    """
    Validate that a stage transition follows the correct order.

    Pipeline order: init -> qigua -> scene_router -> yao_analysis -> reporter -> complete

    Args:
        current: Current stage name.
        target: Target stage name.

    Returns:
        True if transition is valid.
    """
    if current not in VALID_STAGES or target not in VALID_STAGES:
        return False

    current_idx = VALID_STAGES.index(current)
    target_idx = VALID_STAGES.index(target)

    return target_idx == current_idx + 1 or target == current
