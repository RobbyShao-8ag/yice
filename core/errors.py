"""Error types for yice project."""

from typing import List, Dict, Any, Optional


class YiceError(Exception):
    """Base error for yice project."""

    pass


class PartialFailureError(YiceError):
    """Raised when some YaoAgents fail but others succeed.

    This error allows partial results to continue processing
    when not all six yao positions succeed.
    """

    def __init__(
        self,
        failed_positions: List[int],
        successful_positions: List[int],
        partial_results: Dict[int, Any],
    ):
        self.failed_positions = failed_positions
        self.successful_positions = successful_positions
        self.partial_results = partial_results
        message = f"Partial failure: {len(failed_positions)} positions failed, {len(successful_positions)} succeeded"
        super().__init__(message)


class LLMRateLimitError(YiceError):
    """Raised when API returns 429 rate limit error.

    This error triggers retry logic in the LLM client.
    """

    def __init__(self, retry_after: Optional[int] = None, provider: str = "unknown"):
        self.retry_after = retry_after
        self.provider = provider
        message = f"Rate limit exceeded for provider: {provider}"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message)


class LLMCallError(YiceError):
    """Raised when LLM call fails after all retries.

    This error indicates a permanent failure in calling the LLM API,
    either due to network issues, server errors, or exhausted retries.
    """

    def __init__(
        self,
        message: str = "LLM call failed",
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.original_error = original_error
        super().__init__(message)


class DataValidationError(YiceError):
    """Raised when JSON data does not match expected schema.

    This error occurs during startup data validation.
    """

    def __init__(self, file_name: str, expected_schema: str, actual_data: Any):
        self.file_name = file_name
        self.expected_schema = expected_schema
        self.actual_data = actual_data
        message = f"Data validation failed for {file_name}: expected {expected_schema}"
        super().__init__(message)


class DataError(YiceError):
    """Raised when data loading or processing fails.

    This error occurs when JSON files cannot be loaded,
    contain invalid structure, or have duplicate IDs.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
