"""Tests for error types."""

import pytest
from core.errors import (
    YiceError,
    PartialFailureError,
    LLMRateLimitError,
    DataValidationError,
)


class TestYiceError:
    def test_base_error_instantiation(self):
        err = YiceError("test error")
        assert str(err) == "test error"
        assert isinstance(err, Exception)


class TestPartialFailureError:
    def test_partial_failure_error_instantiation(self):
        failed = [1, 3]
        successful = [2, 4, 5, 6]
        results = {2: "result2", 4: "result4", 5: "result5", 6: "result6"}

        err = PartialFailureError(failed, successful, results)

        assert err.failed_positions == failed
        assert err.successful_positions == successful
        assert err.partial_results == results
        assert "Partial failure" in str(err)

    def test_partial_failure_error_message(self):
        err = PartialFailureError([1], [2, 3, 4, 5, 6], {})
        message = str(err)
        assert "1 positions failed" in message
        assert "5 succeeded" in message


class TestLLMRateLimitError:
    def test_rate_limit_error_without_retry(self):
        err = LLMRateLimitError(provider="openai")

        assert err.retry_after is None
        assert err.provider == "openai"
        assert "openai" in str(err)

    def test_rate_limit_error_with_retry(self):
        err = LLMRateLimitError(retry_after=60, provider="anthropic")

        assert err.retry_after == 60
        assert err.provider == "anthropic"
        assert "60" in str(err)

    def test_rate_limit_error_default_provider(self):
        err = LLMRateLimitError()

        assert err.provider == "unknown"


class TestDataValidationError:
    def test_validation_error_instantiation(self):
        err = DataValidationError(
            file_name="hexagrams.json",
            expected_schema="list[dict]",
            actual_data={"invalid": "structure"},
        )

        assert err.file_name == "hexagrams.json"
        assert err.expected_schema == "list[dict]"
        assert err.actual_data == {"invalid": "structure"}
        assert "hexagrams.json" in str(err)

    def test_validation_error_message(self):
        err = DataValidationError(
            file_name="lines.json", expected_schema="array", actual_data=None
        )

        message = str(err)
        assert "lines.json" in message
        assert "expected array" in message
