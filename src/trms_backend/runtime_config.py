from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError, field_validator

RuntimeEnvironment = Literal["development", "test", "production"]

DEFAULT_DATABASE_URL = "sqlite:///./trms.db"
DEFAULT_MATERIAL_STORAGE_DIR = "./data/materials"
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)
VALID_ENVIRONMENTS = frozenset({"development", "test", "production"})


class RuntimeConfigError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("invalid runtime configuration: " + "; ".join(issues))


class RuntimeConfig(BaseModel):
    environment: RuntimeEnvironment
    database_url: str
    material_storage_dir: Path
    cors_allowed_origins: tuple[str, ...]
    public_api_base_url: str
    api_host: str
    api_port: int = Field(ge=1, le=65535)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("database_url must not be empty")
        if "://" not in normalized:
            raise ValueError("database_url must include a scheme")
        return normalized

    @field_validator("material_storage_dir", mode="before")
    @classmethod
    def validate_material_storage_dir(cls, value: str | Path) -> Path:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("material_storage_dir must not be empty")
        return Path(normalized)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def validate_cors_allowed_origins(
        cls,
        value: str | Iterable[str],
    ) -> tuple[str, ...]:
        if isinstance(value, str):
            candidates = [item.strip() for item in value.split(",")]
        else:
            candidates = [str(item).strip() for item in value]

        normalized_origins: list[str] = []
        for candidate in candidates:
            if not candidate:
                continue
            normalized_origin = _normalize_origin(candidate)
            if normalized_origin not in normalized_origins:
                normalized_origins.append(normalized_origin)

        if not normalized_origins:
            raise ValueError("cors_allowed_origins must not be empty")
        return tuple(normalized_origins)

    @field_validator("public_api_base_url")
    @classmethod
    def validate_public_api_base_url(cls, value: str) -> str:
        return _normalize_http_url(
            value,
            field_name="public_api_base_url",
            allow_path=True,
        )

    @field_validator("api_host")
    @classmethod
    def validate_api_host(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("api_host must not be empty")
        if "://" in normalized or "/" in normalized or " " in normalized:
            raise ValueError("api_host must be a bare host or IP address")
        return normalized


def load_runtime_config(
    env: Mapping[str, str] | None = None,
    *,
    environment: str | None = None,
    database_url: str | None = None,
    material_storage_dir: str | Path | None = None,
    cors_allowed_origins: str | Iterable[str] | None = None,
    public_api_base_url: str | None = None,
    api_host: str | None = None,
    api_port: str | int | None = None,
) -> RuntimeConfig:
    environment_variables = os.environ if env is None else env
    raw_environment = environment if environment is not None else environment_variables.get("TRMS_ENV")
    normalized_environment = (raw_environment or "development").strip().lower()
    if normalized_environment not in VALID_ENVIRONMENTS:
        raise RuntimeConfigError(
            [f"TRMS_ENV must be one of: {', '.join(sorted(VALID_ENVIRONMENTS))}"]
        )

    issues: list[str] = []
    require_explicit_values = normalized_environment == "production"

    raw_database_url = _resolve_value(database_url, environment_variables.get("DATABASE_URL"))
    if raw_database_url is None:
        if require_explicit_values:
            issues.append("DATABASE_URL is required when TRMS_ENV=production")
        raw_database_url = DEFAULT_DATABASE_URL

    raw_material_storage_dir = _resolve_value(
        material_storage_dir,
        environment_variables.get("MATERIAL_STORAGE_DIR"),
    )
    if raw_material_storage_dir is None:
        if require_explicit_values:
            issues.append("MATERIAL_STORAGE_DIR is required when TRMS_ENV=production")
        raw_material_storage_dir = DEFAULT_MATERIAL_STORAGE_DIR

    raw_api_host = _resolve_value(api_host, environment_variables.get("TRMS_API_HOST"))
    if raw_api_host is None:
        if require_explicit_values:
            issues.append("TRMS_API_HOST is required when TRMS_ENV=production")
        raw_api_host = DEFAULT_API_HOST

    raw_api_port = _resolve_value(api_port, environment_variables.get("TRMS_API_PORT"))
    if raw_api_port is None:
        if require_explicit_values:
            issues.append("TRMS_API_PORT is required when TRMS_ENV=production")
        raw_api_port = DEFAULT_API_PORT

    raw_cors_allowed_origins = _resolve_value(
        cors_allowed_origins,
        environment_variables.get("TRMS_CORS_ALLOWED_ORIGINS"),
    )
    if raw_cors_allowed_origins is None:
        if require_explicit_values:
            issues.append("TRMS_CORS_ALLOWED_ORIGINS is required when TRMS_ENV=production")
        raw_cors_allowed_origins = DEFAULT_CORS_ALLOWED_ORIGINS

    raw_public_api_base_url = _resolve_value(
        public_api_base_url,
        environment_variables.get("TRMS_PUBLIC_API_BASE_URL"),
    )
    if raw_public_api_base_url is None:
        if require_explicit_values:
            issues.append("TRMS_PUBLIC_API_BASE_URL is required when TRMS_ENV=production")
        raw_public_api_base_url = _build_default_public_api_base_url(
            host=str(raw_api_host),
            port=str(raw_api_port),
        )

    if issues:
        raise RuntimeConfigError(issues)

    try:
        return RuntimeConfig.model_validate(
            {
                "environment": normalized_environment,
                "database_url": raw_database_url,
                "material_storage_dir": raw_material_storage_dir,
                "cors_allowed_origins": raw_cors_allowed_origins,
                "public_api_base_url": raw_public_api_base_url,
                "api_host": raw_api_host,
                "api_port": raw_api_port,
            }
        )
    except ValidationError as error:
        raise RuntimeConfigError(_format_validation_issues(error)) from error


def _resolve_value(explicit_value: object | None, environment_value: object | None) -> object | None:
    if explicit_value is not None:
        return explicit_value
    return environment_value


def _build_default_public_api_base_url(*, host: str, port: str) -> str:
    normalized_host = host.strip() if host.strip() != "0.0.0.0" else DEFAULT_API_HOST
    normalized_port = port.strip()
    return f"http://{normalized_host}:{normalized_port}/api"


def _normalize_origin(value: str) -> str:
    return _normalize_http_url(value, field_name="cors_allowed_origins", allow_path=False)


def _normalize_http_url(value: str, *, field_name: str, allow_path: bool) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute http(s) URL")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not contain params, query, or fragment")
    if not allow_path and parsed.path not in {"", "/"}:
        raise ValueError(f"{field_name} must not contain a path")

    normalized_path = parsed.path.rstrip("/") if allow_path else ""
    if allow_path and not normalized_path:
        normalized_path = ""
    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"


def _format_validation_issues(error: ValidationError) -> list[str]:
    issues: list[str] = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"])
        issues.append(f"{location}: {issue['msg']}")
    return issues
