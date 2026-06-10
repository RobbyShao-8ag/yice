"""Logging configuration for yice."""

import logging
import sys
import json
from datetime import datetime
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in [
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class SensitiveFieldFilter(logging.Filter):
    """Filter to redact sensitive fields from logs."""

    def __init__(self, sensitive_fields: list[str]):
        self.sensitive_fields = sensitive_fields

    def filter(self, record):
        msg = record.getMessage()
        for field in self.sensitive_fields:
            if field in msg:
                msg = msg.replace(
                    f"{field}={record.__dict__.get(field, '***')}",
                    f"{field}=***REDACTED***",
                )
        record.msg = msg
        return True


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    sensitive_fields: Optional[list[str]] = None,
    console_level: Optional[str] = None,
) -> logging.Logger:
    """Setup logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file handler
        json_format: Use JSON format (True) or text format (False)
        sensitive_fields: Fields to redact (e.g., ['api_key', 'password'])
        console_level: Optional console log level. Defaults to level.

    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level or level)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(console_handler)

    if log_file:
        import os

        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    if sensitive_fields:
        root_logger.addFilter(SensitiveFieldFilter(sensitive_fields))

    return root_logger
