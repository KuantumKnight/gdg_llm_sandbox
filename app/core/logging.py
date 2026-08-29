"""Allowlist-based structured logging with defense-in-depth secret redaction."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_LOGGER_NAME = "gdg_sandbox"
_SAFE_FIELDS = (
    "event",
    "request_id",
    "route",
    "method",
    "status",
    "preset_id",
    "outcome",
    "solved",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "exception_class",
)


class SecretRedactionFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self.secrets = [secret for secret in secrets if secret]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for secret in self.secrets:
                record.msg = record.msg.replace(secret, "[REDACTED]")
        return True


class JsonAllowlistFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
        }
        if isinstance(record.msg, str) and record.msg:
            payload["event"] = record.msg
        for field in _SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception_class"] = getattr(record.exc_info[0], "__name__", "Exception")
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_logging(*, level: str, secrets: list[str]) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonAllowlistFormatter())
    handler.addFilter(SecretRedactionFilter(secrets))
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
