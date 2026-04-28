from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr, ValidationError, field_validator
from trms_backend.logging_safety import sanitize_log_fields

RuntimeEnvironment = Literal["development", "test", "production"]
AsyncJobMode = Literal["in_process", "worker"]
DEFAULT_DATABASE_URL = "sqlite:///./trms.db"
DEFAULT_MATERIAL_STORAGE_DIR = "./data/materials"
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0
DEFAULT_LLM_MAX_RETRIES = 2
DEFAULT_ASYNC_JOB_MODE_BY_ENV: dict[RuntimeEnvironment, AsyncJobMode] = {
    "development": "in_process",
    "test": "in_process",
    "production": "worker",
}
DEFAULT_ASYNC_JOB_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_ALLOW_ADMIN_SELF_REGISTER_BY_ENV: dict[RuntimeEnvironment, bool] = {
    "development": True,
    "test": True,
    "production": False,
}
VALID_ENVIRONMENTS = frozenset({"development", "test", "production"})
DEFAULT_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class RuntimeConfigError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("invalid runtime configuration: " + "; ".join(issues))


class LLMProviderConfig(BaseModel):
    api_key: SecretStr
    base_url: str
    model: str
    timeout_seconds: float = Field(gt=0, le=300)
    max_retries: int = Field(ge=0, le=10)

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, value: SecretStr | str) -> SecretStr:
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            raise ValueError("llm_provider.api_key must not be empty")
        return SecretStr(normalized)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return _normalize_http_url(value, field_name="llm_provider.base_url", allow_path=True)

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("llm_provider.model must not be empty")
        return normalized

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "api_key": "[redacted]",
            "api_key_configured": True,
            }
        )


class AsyncJobConfig(BaseModel):
    mode: AsyncJobMode
    worker_poll_interval_seconds: float = Field(gt=0, le=300)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"in_process", "worker"}:
            raise ValueError("async_jobs.mode must be one of: in_process, worker")
        return normalized


class AuthConfig(BaseModel):
    allow_admin_self_register: bool
    bootstrap_admin_token: SecretStr | None = None

    @field_validator("allow_admin_self_register", mode="before")
    @classmethod
    def validate_allow_admin_self_register(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError("auth.allow_admin_self_register must be a boolean")

    @field_validator("bootstrap_admin_token", mode="before")
    @classmethod
    def validate_bootstrap_admin_token(
        cls,
        value: SecretStr | str | None,
    ) -> SecretStr | None:
        if value is None:
            return None
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            return None
        return SecretStr(normalized)

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
            "allow_admin_self_register": self.allow_admin_self_register,
            "bootstrap_admin_token": "[redacted]" if self.bootstrap_admin_token else None,
            "bootstrap_admin_token_configured": self.bootstrap_admin_token is not None,
            }
        )


class LocalFileStorageConfig(BaseModel):
    backend: Literal["local"]
    root_dir: Path

    @field_validator("root_dir", mode="before")
    @classmethod
    def validate_root_dir(cls, value: str | Path) -> Path:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("file_storage.root_dir must not be empty")
        return Path(normalized)

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
            "backend": self.backend,
            "root_dir": str(self.root_dir),
            }
        )


class S3FileStorageConfig(BaseModel):
    backend: Literal["s3"]
    endpoint: str
    bucket: str
    access_key_id: SecretStr
    secret_access_key: SecretStr
    region: str | None = None
    key_prefix: str | None = None

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        return _normalize_http_url(value, field_name="file_storage.endpoint", allow_path=False)

    @field_validator("bucket")
    @classmethod
    def validate_bucket(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("file_storage.bucket must not be empty")
        if "/" in normalized:
            raise ValueError("file_storage.bucket must not contain '/'")
        return normalized

    @field_validator("access_key_id", "secret_access_key", mode="before")
    @classmethod
    def validate_secret_field(cls, value: SecretStr | str, info) -> SecretStr:
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            raise ValueError(f"file_storage.{info.field_name} must not be empty")
        return SecretStr(normalized)

    @field_validator("region")
    @classmethod
    def validate_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("key_prefix")
    @classmethod
    def validate_key_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().strip("/")
        return normalized or None

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
            "backend": self.backend,
            "endpoint": self.endpoint,
            "bucket": self.bucket,
            "region": self.region,
            "key_prefix": self.key_prefix,
            "access_key_id": "[redacted]",
            "secret_access_key": "[redacted]",
            "credentials_configured": True,
            }
        )


FileStorageConfig = Annotated[
    LocalFileStorageConfig | S3FileStorageConfig,
    Field(discriminator="backend"),
]


class RuntimeConfig(BaseModel):
    environment: RuntimeEnvironment
    database_url: str
    file_storage: FileStorageConfig
    cors_allowed_origins: tuple[str, ...]
    public_api_base_url: str
    api_host: str
    api_port: int = Field(ge=1, le=65535)
    async_jobs: AsyncJobConfig
    auth: AuthConfig
    llm_provider: LLMProviderConfig | None = None

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("database_url must not be empty")
        if "://" not in normalized:
            raise ValueError("database_url must include a scheme")
        return normalized

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

    @property
    def material_storage_dir(self) -> Path:
        if isinstance(self.file_storage, LocalFileStorageConfig):
            return self.file_storage.root_dir
        raise RuntimeError("material_storage_dir is only available for local file storage")

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
                "environment": self.environment,
                "database_url": self.database_url,
                "file_storage": self.file_storage.to_safe_log_fields(),
                "cors_allowed_origins": list(self.cors_allowed_origins),
                "public_api_base_url": self.public_api_base_url,
                "api_host": self.api_host,
                "api_port": self.api_port,
                "async_jobs": {
                    "mode": self.async_jobs.mode,
                    "worker_poll_interval_seconds": self.async_jobs.worker_poll_interval_seconds,
                },
                "auth": self.auth.to_safe_log_fields(),
                "llm_provider": (
                    self.llm_provider.to_safe_log_fields() if self.llm_provider is not None else None
                ),
            }
        )


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
    storage_backend: str | None = None,
    storage_s3_endpoint: str | None = None,
    storage_s3_bucket: str | None = None,
    storage_s3_access_key_id: str | None = None,
    storage_s3_secret_access_key: str | None = None,
    storage_s3_region: str | None = None,
    storage_s3_key_prefix: str | None = None,
    async_job_mode: str | None = None,
    async_job_poll_interval_seconds: str | float | int | None = None,
    auth_allow_admin_self_register: bool | str | None = None,
    auth_bootstrap_admin_token: str | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_timeout_seconds: str | float | int | None = None,
    llm_max_retries: str | int | None = None,
) -> RuntimeConfig:
    environment_variables = _load_environment_variables(env)
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

    raw_storage_backend = _resolve_value(
        storage_backend,
        environment_variables.get("TRMS_STORAGE_BACKEND"),
    )
    if raw_storage_backend is None:
        if require_explicit_values:
            issues.append("TRMS_STORAGE_BACKEND is required when TRMS_ENV=production")
        raw_storage_backend = "local"

    raw_material_storage_dir = _resolve_value(
        material_storage_dir,
        environment_variables.get("MATERIAL_STORAGE_DIR"),
    )
    raw_storage_s3_endpoint = _resolve_value(
        storage_s3_endpoint,
        environment_variables.get("TRMS_STORAGE_S3_ENDPOINT"),
    )
    raw_storage_s3_bucket = _resolve_value(
        storage_s3_bucket,
        environment_variables.get("TRMS_STORAGE_S3_BUCKET"),
    )
    raw_storage_s3_access_key_id = _resolve_value(
        storage_s3_access_key_id,
        environment_variables.get("TRMS_STORAGE_S3_ACCESS_KEY_ID"),
    )
    raw_storage_s3_secret_access_key = _resolve_value(
        storage_s3_secret_access_key,
        environment_variables.get("TRMS_STORAGE_S3_SECRET_ACCESS_KEY"),
    )
    raw_storage_s3_region = _resolve_value(
        storage_s3_region,
        environment_variables.get("TRMS_STORAGE_S3_REGION"),
    )
    raw_storage_s3_key_prefix = _resolve_value(
        storage_s3_key_prefix,
        environment_variables.get("TRMS_STORAGE_S3_KEY_PREFIX"),
    )

    raw_llm_api_key = _resolve_value(llm_api_key, environment_variables.get("TRMS_LLM_API_KEY"))
    raw_llm_base_url = _resolve_value(
        llm_base_url,
        environment_variables.get("TRMS_LLM_BASE_URL"),
    )
    raw_llm_model = _resolve_value(llm_model, environment_variables.get("TRMS_LLM_MODEL"))
    raw_llm_timeout_seconds = _resolve_value(
        llm_timeout_seconds,
        environment_variables.get("TRMS_LLM_TIMEOUT_SECONDS"),
    )
    raw_llm_max_retries = _resolve_value(
        llm_max_retries,
        environment_variables.get("TRMS_LLM_MAX_RETRIES"),
    )
    raw_async_job_mode = _resolve_value(
        async_job_mode,
        environment_variables.get("TRMS_ASYNC_JOB_MODE"),
    )
    if raw_async_job_mode is None:
        raw_async_job_mode = DEFAULT_ASYNC_JOB_MODE_BY_ENV[normalized_environment]
    raw_async_job_poll_interval_seconds = _resolve_value(
        async_job_poll_interval_seconds,
        environment_variables.get("TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS"),
    )
    if raw_async_job_poll_interval_seconds is None:
        raw_async_job_poll_interval_seconds = DEFAULT_ASYNC_JOB_POLL_INTERVAL_SECONDS
    raw_auth_allow_admin_self_register = _resolve_value(
        auth_allow_admin_self_register,
        environment_variables.get("TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER"),
    )
    if raw_auth_allow_admin_self_register is None:
        raw_auth_allow_admin_self_register = DEFAULT_ALLOW_ADMIN_SELF_REGISTER_BY_ENV[
            normalized_environment
        ]
    raw_auth_bootstrap_admin_token = _resolve_value(
        auth_bootstrap_admin_token,
        environment_variables.get("TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN"),
    )

    if normalized_environment == "production" and str(raw_async_job_mode).strip() == "in_process":
        issues.append(
            "TRMS_ASYNC_JOB_MODE=in_process is not allowed when TRMS_ENV=production; "
            "configure worker mode instead"
        )

    normalized_storage_backend = str(raw_storage_backend).strip().lower()
    storage_payload: dict[str, object]
    if normalized_storage_backend == "local":
        if normalized_environment == "production":
            issues.append(
                "TRMS_STORAGE_BACKEND=local is not allowed when TRMS_ENV=production; "
                "configure s3 storage instead"
            )
        if raw_material_storage_dir is None:
            raw_material_storage_dir = DEFAULT_MATERIAL_STORAGE_DIR
        storage_payload = {
            "backend": "local",
            "root_dir": raw_material_storage_dir,
        }
    elif normalized_storage_backend == "s3":
        if not _has_meaningful_value(raw_storage_s3_endpoint):
            issues.append("TRMS_STORAGE_S3_ENDPOINT is required when TRMS_STORAGE_BACKEND=s3")
        if not _has_meaningful_value(raw_storage_s3_bucket):
            issues.append("TRMS_STORAGE_S3_BUCKET is required when TRMS_STORAGE_BACKEND=s3")
        if not _has_meaningful_value(raw_storage_s3_access_key_id):
            issues.append(
                "TRMS_STORAGE_S3_ACCESS_KEY_ID is required when TRMS_STORAGE_BACKEND=s3"
            )
        if not _has_meaningful_value(raw_storage_s3_secret_access_key):
            issues.append(
                "TRMS_STORAGE_S3_SECRET_ACCESS_KEY is required when TRMS_STORAGE_BACKEND=s3"
            )
        storage_payload = {
            "backend": "s3",
            "endpoint": raw_storage_s3_endpoint,
            "bucket": raw_storage_s3_bucket,
            "access_key_id": raw_storage_s3_access_key_id,
            "secret_access_key": raw_storage_s3_secret_access_key,
            "region": raw_storage_s3_region,
            "key_prefix": raw_storage_s3_key_prefix,
        }
    else:
        storage_payload = {"backend": raw_storage_backend}

    llm_provider_payload: dict[str, object] | None = None
    if any(
        value is not None
        for value in (
            raw_llm_api_key,
            raw_llm_base_url,
            raw_llm_model,
            raw_llm_timeout_seconds,
            raw_llm_max_retries,
        )
    ):
        if not _has_meaningful_value(raw_llm_api_key):
            issues.append(
                "TRMS_LLM_API_KEY is required when any TRMS_LLM_* setting is configured"
            )
        if not _has_meaningful_value(raw_llm_model):
            issues.append(
                "TRMS_LLM_MODEL is required when any TRMS_LLM_* setting is configured"
            )
        llm_provider_payload = {
            "api_key": raw_llm_api_key,
            "base_url": (
                raw_llm_base_url if raw_llm_base_url is not None else DEFAULT_LLM_BASE_URL
            ),
            "model": raw_llm_model,
            "timeout_seconds": (
                raw_llm_timeout_seconds
                if raw_llm_timeout_seconds is not None
                else DEFAULT_LLM_TIMEOUT_SECONDS
            ),
            "max_retries": (
                raw_llm_max_retries
                if raw_llm_max_retries is not None
                else DEFAULT_LLM_MAX_RETRIES
            ),
        }

    if issues:
        raise RuntimeConfigError(issues)

    try:
        return RuntimeConfig.model_validate(
            {
                "environment": normalized_environment,
                "database_url": raw_database_url,
                "file_storage": storage_payload,
                "cors_allowed_origins": raw_cors_allowed_origins,
                "public_api_base_url": raw_public_api_base_url,
                "api_host": raw_api_host,
                "api_port": raw_api_port,
                "async_jobs": {
                    "mode": raw_async_job_mode,
                    "worker_poll_interval_seconds": raw_async_job_poll_interval_seconds,
                },
                "auth": {
                    "allow_admin_self_register": raw_auth_allow_admin_self_register,
                    "bootstrap_admin_token": raw_auth_bootstrap_admin_token,
                },
                "llm_provider": llm_provider_payload,
            }
        )
    except ValidationError as error:
        raise RuntimeConfigError(_format_validation_issues(error)) from error


def _resolve_value(explicit_value: object | None, environment_value: object | None) -> object | None:
    if explicit_value is not None:
        return explicit_value
    return environment_value


def _load_environment_variables(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env

    dotenv_values = _read_dotenv_file(DEFAULT_DOTENV_PATH)
    if not dotenv_values:
        return os.environ

    merged_environment = dict(dotenv_values)
    merged_environment.update(os.environ)
    return merged_environment


def _read_dotenv_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()

        key, separator, value = line.partition("=")
        if separator != "=":
            continue

        normalized_key = key.strip()
        if not normalized_key:
            continue

        normalized_value = value.strip()
        if normalized_value and normalized_value[0] not in {'"', "'"}:
            comment_index = normalized_value.find(" #")
            if comment_index != -1:
                normalized_value = normalized_value[:comment_index].rstrip()

        values[normalized_key] = _strip_optional_quotes(normalized_value)

    return values


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _has_meaningful_value(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, SecretStr):
        return bool(value.get_secret_value().strip())
    if isinstance(value, str):
        return bool(value.strip())
    return True


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
