from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit


REDACTED_LOG_VALUE = "[redacted]"
REDACTED_LOG_PATH = "[redacted-path]"
_SENSITIVE_LOG_KEYWORDS = (
    "password",
    "secret",
    "token",
    "oauth",
    "authorization",
    "cookie",
    "api_key",
    "access_key",
    "refresh_token",
)
_PATH_LOG_KEYWORDS = (
    "path",
    "root_dir",
    "directory",
    "storage_key",
    "storage_path",
)
_FILE_URL_LOG_KEYWORDS = (
    "file_url",
    "download_url",
    "artifact_url",
    "storage_url",
)
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|secret|token|oauth|api[_-]?key|authorization|cookie|access[_-]?key|refresh[_-]?token)\b\s*[:=]\s*([^\s,;]+)"
)
_AUTHORIZATION_BEARER_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\bauthorization\b\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]+"
)
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


def sanitize_log_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: sanitize_log_value(key, value)
        for key, value in fields.items()
    }


def sanitize_log_value(key: str, value: Any) -> Any:
    normalized_key = key.strip().lower()
    if any(keyword in normalized_key for keyword in _SENSITIVE_LOG_KEYWORDS):
        if value is None or isinstance(value, bool):
            return value
        return REDACTED_LOG_VALUE
    if any(keyword in normalized_key for keyword in _FILE_URL_LOG_KEYWORDS):
        return sanitize_file_url_for_log(value)
    if any(keyword in normalized_key for keyword in _PATH_LOG_KEYWORDS):
        return sanitize_local_path_for_log(value)
    return _sanitize_generic_log_value(value)


def sanitize_file_url_for_log(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Path):
        return REDACTED_LOG_PATH
    if not isinstance(value, str):
        return _sanitize_generic_log_value(value)

    normalized = value.strip()
    if not normalized:
        return normalized

    split_result = urlsplit(normalized)
    if not split_result.scheme:
        return REDACTED_LOG_PATH
    return _redact_url_path(split_result)


def sanitize_local_path_for_log(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Path):
        return REDACTED_LOG_PATH
    if isinstance(value, str):
        normalized = value.strip()
        return REDACTED_LOG_PATH if normalized else normalized
    return _sanitize_generic_log_value(value)


def sanitize_log_text(value: str) -> str:
    sanitized = value.strip()
    sanitized = _AUTHORIZATION_BEARER_ASSIGNMENT_PATTERN.sub(
        "authorization=[redacted]",
        sanitized,
    )
    sanitized = _BEARER_TOKEN_PATTERN.sub("Bearer [redacted]", sanitized)
    return _SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1=[redacted]", sanitized)


def _sanitize_generic_log_value(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return sanitize_log_text(value)
    if isinstance(value, Path):
        return REDACTED_LOG_PATH
    if isinstance(value, Mapping):
        return sanitize_log_fields({str(key): item for key, item in value.items()})
    if isinstance(value, list):
        return [_sanitize_generic_log_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_generic_log_value(item) for item in value)
    if isinstance(value, set):
        return {_sanitize_generic_log_value(item) for item in value}
    return value


def _redact_url_path(split_result: SplitResult) -> str:
    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            f"/{REDACTED_LOG_PATH}",
            "",
            "",
        )
    )
