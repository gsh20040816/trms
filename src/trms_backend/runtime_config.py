from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, SecretStr, ValidationError, field_validator
from trms_backend.domain.system_ai_provider_config import (
    SystemAiProviderConfig,
    SystemAiProviderOverride,
)
from trms_backend.logging_safety import sanitize_log_fields

RuntimeEnvironment = Literal["development", "test", "production"]
AsyncJobMode = Literal["in_process", "worker"]
DEFAULT_DATABASE_URL = "sqlite:///./trms.db"
DEFAULT_MATERIAL_STORAGE_DIR = "./data/materials"
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 9876
DEFAULT_SYSTEM_TIMEZONE = "UTC"
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
DEFAULT_ASYNC_JOB_WORKER_CONCURRENCY = 4
DEFAULT_ALLOW_ADMIN_SELF_REGISTER_BY_ENV: dict[RuntimeEnvironment, bool] = {
    "development": True,
    "test": True,
    "production": False,
}
VALID_ENVIRONMENTS = frozenset({"development", "test", "production"})
DEFAULT_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
DOTENV_PATH_ENVIRONMENT_KEY = "TRMS_DOTENV_PATH"


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
    worker_concurrency: int = Field(ge=1, le=32)

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
    telegram_inbound_token: SecretStr | None = None
    email_inbound_token: SecretStr | None = None

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

    @field_validator("telegram_inbound_token", mode="before")
    @classmethod
    def validate_telegram_inbound_token(
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

    @field_validator("email_inbound_token", mode="before")
    @classmethod
    def validate_email_inbound_token(
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
                "telegram_inbound_token": "[redacted]" if self.telegram_inbound_token else None,
                "telegram_inbound_token_configured": self.telegram_inbound_token is not None,
                "email_inbound_token": "[redacted]" if self.email_inbound_token else None,
                "email_inbound_token_configured": self.email_inbound_token is not None,
            }
        )


class TelegramBotConfig(BaseModel):
    token: SecretStr
    webhook_secret: SecretStr | None = None

    @field_validator("token", mode="before")
    @classmethod
    def validate_token(cls, value: SecretStr | str) -> SecretStr:
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            raise ValueError("telegram_bot.token must not be empty")
        return SecretStr(normalized)

    @field_validator("webhook_secret", mode="before")
    @classmethod
    def validate_webhook_secret(
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
                "token": "[redacted]",
                "token_configured": True,
                "webhook_secret": "[redacted]" if self.webhook_secret is not None else None,
                "webhook_secret_configured": self.webhook_secret is not None,
            }
        )


class SubmissionGuideConfig(BaseModel):
    email_submission_address: str | None = None
    telegram_bot_url: str | None = None

    @field_validator("email_submission_address", mode="before")
    @classmethod
    def validate_email_submission_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return _normalize_email_address(
            normalized,
            field_name="submission_guide.email_submission_address",
        )

    @field_validator("telegram_bot_url", mode="before")
    @classmethod
    def validate_telegram_bot_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return _normalize_http_url(
            normalized,
            field_name="submission_guide.telegram_bot_url",
            allow_path=True,
        )


class OutboundEmailConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    username: str | None = None
    password: SecretStr | None = None
    from_address: str
    starttls: bool = True
    use_ssl: bool = False
    timeout_seconds: float = Field(gt=0, le=300)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("outbound_email.host must not be empty")
        if "://" in normalized or "/" in normalized or " " in normalized:
            raise ValueError("outbound_email.host must be a bare host or IP address")
        return normalized

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: SecretStr | str | None) -> SecretStr | None:
        if value is None:
            return None
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            return None
        return SecretStr(normalized)

    @field_validator("from_address")
    @classmethod
    def validate_from_address(cls, value: str) -> str:
        return _normalize_email_address(value, field_name="outbound_email.from_address")

    @field_validator("starttls", "use_ssl", mode="before")
    @classmethod
    def validate_bool_fields(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError("outbound_email boolean fields must be a boolean")

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
                "host": self.host,
                "port": self.port,
                "username": self.username,
                "password": "[redacted]" if self.password is not None else None,
                "password_configured": self.password is not None,
                "from_address": self.from_address,
                "starttls": self.starttls,
                "use_ssl": self.use_ssl,
                "timeout_seconds": self.timeout_seconds,
            }
        )


class EmailInboxConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    username: str
    password: SecretStr
    mailbox: str = "INBOX"
    poll_interval_seconds: float = Field(gt=0, le=3600)
    use_ssl: bool = True
    starttls: bool = False

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("email_inbox.host must not be empty")
        if "://" in normalized or "/" in normalized or " " in normalized:
            raise ValueError("email_inbox.host must be a bare host or IP address")
        return normalized

    @field_validator("username", "mailbox")
    @classmethod
    def validate_text_field(cls, value: str, info) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"email_inbox.{info.field_name} must not be empty")
        return normalized

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: SecretStr | str) -> SecretStr:
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            raise ValueError("email_inbox.password must not be empty")
        return SecretStr(normalized)

    @field_validator("use_ssl", "starttls", mode="before")
    @classmethod
    def validate_bool_fields(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError("email_inbox boolean fields must be a boolean")

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
                "host": self.host,
                "port": self.port,
                "username": self.username,
                "password": "[redacted]",
                "password_configured": True,
                "mailbox": self.mailbox,
                "poll_interval_seconds": self.poll_interval_seconds,
                "use_ssl": self.use_ssl,
                "starttls": self.starttls,
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
    public_web_base_url: str
    system_timezone: str
    api_host: str
    api_port: int = Field(ge=1, le=65535)
    async_jobs: AsyncJobConfig
    auth: AuthConfig
    submission_guide: SubmissionGuideConfig = Field(default_factory=SubmissionGuideConfig)
    telegram_bot: TelegramBotConfig | None = None
    outbound_email: OutboundEmailConfig | None = None
    email_inbox: EmailInboxConfig | None = None
    text_llm_provider: LLMProviderConfig | None = None
    vlm_provider: LLMProviderConfig | None = None

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

    @field_validator("public_web_base_url")
    @classmethod
    def validate_public_web_base_url(cls, value: str) -> str:
        return _normalize_http_url(
            value,
            field_name="public_web_base_url",
            allow_path=True,
        )

    @field_validator("system_timezone")
    @classmethod
    def validate_system_timezone(cls, value: str) -> str:
        return _normalize_timezone_name(value, field_name="system_timezone")

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

    @property
    def llm_provider(self) -> LLMProviderConfig | None:
        return self.text_llm_provider or self.vlm_provider

    def to_safe_log_fields(self) -> dict[str, object]:
        return sanitize_log_fields(
            {
                "environment": self.environment,
                "database_url": self.database_url,
                "file_storage": self.file_storage.to_safe_log_fields(),
                "cors_allowed_origins": list(self.cors_allowed_origins),
                "public_api_base_url": self.public_api_base_url,
                "public_web_base_url": self.public_web_base_url,
                "system_timezone": self.system_timezone,
                "api_host": self.api_host,
                "api_port": self.api_port,
                "async_jobs": {
                    "mode": self.async_jobs.mode,
                    "worker_poll_interval_seconds": self.async_jobs.worker_poll_interval_seconds,
                    "worker_concurrency": self.async_jobs.worker_concurrency,
                },
                "auth": self.auth.to_safe_log_fields(),
                "submission_guide": self.submission_guide.model_dump(),
                "telegram_bot": (
                    self.telegram_bot.to_safe_log_fields()
                    if self.telegram_bot is not None
                    else None
                ),
                "outbound_email": (
                    self.outbound_email.to_safe_log_fields()
                    if self.outbound_email is not None
                    else None
                ),
                "email_inbox": (
                    self.email_inbox.to_safe_log_fields()
                    if self.email_inbox is not None
                    else None
                ),
                "llm_provider": (
                    self.llm_provider.to_safe_log_fields() if self.llm_provider is not None else None
                ),
                "text_llm_provider": (
                    self.text_llm_provider.to_safe_log_fields()
                    if self.text_llm_provider is not None
                    else None
                ),
                "vlm_provider": (
                    self.vlm_provider.to_safe_log_fields()
                    if self.vlm_provider is not None
                    else None
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
    public_web_base_url: str | None = None,
    system_timezone: str | None = None,
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
    async_job_worker_concurrency: str | int | None = None,
    auth_allow_admin_self_register: bool | str | None = None,
    auth_bootstrap_admin_token: str | None = None,
    auth_telegram_inbound_token: str | None = None,
    auth_email_inbound_token: str | None = None,
    telegram_bot_token: str | None = None,
    telegram_webhook_secret: str | None = None,
    public_email_submission_address: str | None = None,
    telegram_bot_url: str | None = None,
    imap_host: str | None = None,
    imap_port: str | int | None = None,
    imap_username: str | None = None,
    imap_password: str | None = None,
    imap_mailbox: str | None = None,
    imap_poll_interval_seconds: str | float | int | None = None,
    imap_use_ssl: bool | str | None = None,
    imap_starttls: bool | str | None = None,
    smtp_host: str | None = None,
    smtp_port: str | int | None = None,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    smtp_from_address: str | None = None,
    smtp_starttls: bool | str | None = None,
    smtp_use_ssl: bool | str | None = None,
    smtp_timeout_seconds: str | float | int | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_timeout_seconds: str | float | int | None = None,
    llm_max_retries: str | int | None = None,
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
    raw_public_web_base_url = _resolve_value(
        public_web_base_url,
        environment_variables.get("TRMS_PUBLIC_WEB_BASE_URL"),
    )
    if raw_public_web_base_url is None:
        raw_public_web_base_url = _build_default_public_web_base_url(
            public_api_base_url=str(raw_public_api_base_url),
        )
    raw_system_timezone = _resolve_value(system_timezone, environment_variables.get("TZ"))
    if raw_system_timezone is None:
        raw_system_timezone = DEFAULT_SYSTEM_TIMEZONE

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

    text_llm_provider_payload = _resolve_provider_payload(
        explicit={
            "api_key": llm_api_key,
            "base_url": llm_base_url,
            "model": llm_model,
            "timeout_seconds": llm_timeout_seconds,
            "max_retries": llm_max_retries,
        },
        env=environment_variables,
        prefix="TRMS_TEXT_LLM",
        legacy_prefix="TRMS_LLM",
        issues=issues,
    )
    vlm_provider_payload = _resolve_provider_payload(
        explicit=None,
        env=environment_variables,
        prefix="TRMS_VLM",
        legacy_prefix="TRMS_LLM",
        issues=issues,
        validate_legacy_missing=False,
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
    raw_async_job_worker_concurrency = _resolve_value(
        async_job_worker_concurrency,
        environment_variables.get("TRMS_ASYNC_JOB_WORKER_CONCURRENCY"),
    )
    if raw_async_job_worker_concurrency is None:
        raw_async_job_worker_concurrency = DEFAULT_ASYNC_JOB_WORKER_CONCURRENCY
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
    raw_auth_telegram_inbound_token = _resolve_value(
        auth_telegram_inbound_token,
        environment_variables.get("TRMS_AUTH_TELEGRAM_INBOUND_TOKEN"),
    )
    raw_auth_email_inbound_token = _resolve_value(
        auth_email_inbound_token,
        environment_variables.get("TRMS_AUTH_EMAIL_INBOUND_TOKEN"),
    )
    raw_telegram_bot_token = _resolve_value(
        telegram_bot_token,
        environment_variables.get("TRMS_TELEGRAM_BOT_TOKEN"),
    )
    raw_telegram_webhook_secret = _resolve_value(
        telegram_webhook_secret,
        environment_variables.get("TRMS_TELEGRAM_WEBHOOK_SECRET"),
    )
    raw_public_email_submission_address = _resolve_value(
        public_email_submission_address,
        environment_variables.get("TRMS_PUBLIC_EMAIL_SUBMISSION_ADDRESS"),
    )
    raw_telegram_bot_url = _resolve_value(
        telegram_bot_url,
        environment_variables.get("TRMS_TELEGRAM_BOT_URL"),
    )
    outbound_email_payload = _resolve_outbound_email_payload(
        explicit={
            "host": smtp_host,
            "port": smtp_port,
            "username": smtp_username,
            "password": smtp_password,
            "from_address": smtp_from_address,
            "starttls": smtp_starttls,
            "use_ssl": smtp_use_ssl,
            "timeout_seconds": smtp_timeout_seconds,
        },
        env=environment_variables,
        issues=issues,
    )
    email_inbox_payload = _resolve_email_inbox_payload(
        explicit={
            "host": imap_host,
            "port": imap_port,
            "username": imap_username,
            "password": imap_password,
            "mailbox": imap_mailbox,
            "poll_interval_seconds": imap_poll_interval_seconds,
            "use_ssl": imap_use_ssl,
            "starttls": imap_starttls,
        },
        env=environment_variables,
        issues=issues,
    )
    raw_public_email_submission_address = _resolve_public_email_submission_address(
        explicit=raw_public_email_submission_address,
        email_inbox_payload=email_inbox_payload,
    )

    if normalized_environment == "production" and str(raw_async_job_mode).strip() == "in_process":
        issues.append(
            "TRMS_ASYNC_JOB_MODE=in_process is not allowed when TRMS_ENV=production; "
            "configure worker mode instead"
        )

    normalized_storage_backend = str(raw_storage_backend).strip().lower()
    storage_payload: dict[str, object]
    if normalized_storage_backend == "local":
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
                "public_web_base_url": raw_public_web_base_url,
                "system_timezone": raw_system_timezone,
                "api_host": raw_api_host,
                "api_port": raw_api_port,
                "async_jobs": {
                    "mode": raw_async_job_mode,
                    "worker_poll_interval_seconds": raw_async_job_poll_interval_seconds,
                    "worker_concurrency": raw_async_job_worker_concurrency,
                },
                "auth": {
                    "allow_admin_self_register": raw_auth_allow_admin_self_register,
                    "bootstrap_admin_token": raw_auth_bootstrap_admin_token,
                    "telegram_inbound_token": raw_auth_telegram_inbound_token,
                    "email_inbound_token": raw_auth_email_inbound_token,
                },
                "submission_guide": {
                    "email_submission_address": raw_public_email_submission_address,
                    "telegram_bot_url": raw_telegram_bot_url,
                },
                "telegram_bot": (
                    {
                        "token": raw_telegram_bot_token,
                        "webhook_secret": raw_telegram_webhook_secret,
                    }
                    if _has_meaningful_value(raw_telegram_bot_token)
                    else None
                ),
                "outbound_email": outbound_email_payload,
                "email_inbox": email_inbox_payload,
                "text_llm_provider": text_llm_provider_payload,
                "vlm_provider": vlm_provider_payload,
            }
        )
    except ValidationError as error:
        raise RuntimeConfigError(_format_validation_issues(error)) from error


def _resolve_value(explicit_value: object | None, environment_value: object | None) -> object | None:
    if explicit_value is not None:
        return explicit_value
    return environment_value


def _resolve_public_email_submission_address(
    *,
    explicit: object | None,
    email_inbox_payload: dict[str, object] | None,
) -> object | None:
    if explicit is not None:
        return explicit
    if email_inbox_payload is None:
        return None
    username = email_inbox_payload.get("username")
    if not isinstance(username, str):
        return None
    try:
        return _normalize_email_address(username, field_name="TRMS_IMAP_USERNAME")
    except ValueError:
        return None


def _resolve_provider_payload(
    *,
    explicit: Mapping[str, object | None] | None,
    env: Mapping[str, str],
    prefix: str,
    legacy_prefix: str,
    issues: list[str],
    validate_legacy_missing: bool = True,
) -> dict[str, object] | None:
    explicit_values = explicit or {}
    explicit_has_values = any(value is not None for value in explicit_values.values())
    prefixed_values = {
        "api_key": env.get(f"{prefix}_API_KEY"),
        "base_url": env.get(f"{prefix}_BASE_URL"),
        "model": env.get(f"{prefix}_MODEL"),
        "timeout_seconds": env.get(f"{prefix}_TIMEOUT_SECONDS"),
        "max_retries": env.get(f"{prefix}_MAX_RETRIES"),
    }
    prefixed_has_values = any(value is not None for value in prefixed_values.values())
    legacy_values = {
        "api_key": env.get(f"{legacy_prefix}_API_KEY"),
        "base_url": env.get(f"{legacy_prefix}_BASE_URL"),
        "model": env.get(f"{legacy_prefix}_MODEL"),
        "timeout_seconds": env.get(f"{legacy_prefix}_TIMEOUT_SECONDS"),
        "max_retries": env.get(f"{legacy_prefix}_MAX_RETRIES"),
    }
    legacy_has_values = any(value is not None for value in legacy_values.values())

    if not explicit_has_values and not prefixed_has_values and not legacy_has_values:
        return None

    source_values = prefixed_values if prefixed_has_values else legacy_values
    using_legacy_values = not prefixed_has_values and legacy_has_values
    if explicit_has_values:
        source_values = {
            **source_values,
            **{key: value for key, value in explicit_values.items() if value is not None},
        }

    api_key = source_values.get("api_key")
    model = source_values.get("model")
    issue_prefix = legacy_prefix if using_legacy_values else prefix
    if not _has_meaningful_value(api_key) and (validate_legacy_missing or not using_legacy_values):
        issues.append(
            f"{issue_prefix}_API_KEY is required when any {issue_prefix}_* setting is configured"
        )
    if not _has_meaningful_value(model) and (validate_legacy_missing or not using_legacy_values):
        issues.append(
            f"{issue_prefix}_MODEL is required when any {issue_prefix}_* setting is configured"
        )
    return {
        "api_key": api_key,
        "base_url": (
            source_values.get("base_url")
            if source_values.get("base_url") is not None
            else DEFAULT_LLM_BASE_URL
        ),
        "model": model,
        "timeout_seconds": (
            source_values.get("timeout_seconds")
            if source_values.get("timeout_seconds") is not None
            else DEFAULT_LLM_TIMEOUT_SECONDS
        ),
        "max_retries": (
            source_values.get("max_retries")
            if source_values.get("max_retries") is not None
            else DEFAULT_LLM_MAX_RETRIES
        ),
    }


def _resolve_outbound_email_payload(
    *,
    explicit: Mapping[str, object | None],
    env: Mapping[str, str],
    issues: list[str],
) -> dict[str, object] | None:
    explicit_has_values = any(value is not None for value in explicit.values())
    env_values = {
        "host": env.get("TRMS_SMTP_HOST"),
        "port": env.get("TRMS_SMTP_PORT"),
        "username": env.get("TRMS_SMTP_USERNAME"),
        "password": env.get("TRMS_SMTP_PASSWORD"),
        "from_address": env.get("TRMS_SMTP_FROM_ADDRESS"),
        "starttls": env.get("TRMS_SMTP_STARTTLS"),
        "use_ssl": env.get("TRMS_SMTP_USE_SSL"),
        "timeout_seconds": env.get("TRMS_SMTP_TIMEOUT_SECONDS"),
    }
    env_has_values = any(value is not None for value in env_values.values())
    if not explicit_has_values and not env_has_values:
        return None

    values = dict(env_values)
    for key, value in explicit.items():
        if value is not None:
            values[key] = value

    if not _has_meaningful_value(values.get("host")):
        issues.append("TRMS_SMTP_HOST is required when any TRMS_SMTP_* setting is configured")
    if not _has_meaningful_value(values.get("port")):
        issues.append("TRMS_SMTP_PORT is required when any TRMS_SMTP_* setting is configured")
    if not _has_meaningful_value(values.get("from_address")):
        issues.append(
            "TRMS_SMTP_FROM_ADDRESS is required when any TRMS_SMTP_* setting is configured"
        )

    has_username = _has_meaningful_value(values.get("username"))
    has_password = _has_meaningful_value(values.get("password"))
    if has_username != has_password:
        issues.append(
            "TRMS_SMTP_USERNAME and TRMS_SMTP_PASSWORD must be configured together"
        )

    return {
        "host": values.get("host"),
        "port": values.get("port"),
        "username": values.get("username"),
        "password": values.get("password"),
        "from_address": values.get("from_address"),
        "starttls": values.get("starttls") if values.get("starttls") is not None else True,
        "use_ssl": values.get("use_ssl") if values.get("use_ssl") is not None else False,
        "timeout_seconds": (
            values.get("timeout_seconds")
            if values.get("timeout_seconds") is not None
            else 15.0
        ),
    }


def _resolve_email_inbox_payload(
    *,
    explicit: Mapping[str, object | None],
    env: Mapping[str, str],
    issues: list[str],
) -> dict[str, object] | None:
    explicit_has_values = any(value is not None for value in explicit.values())
    env_values = {
        "host": env.get("TRMS_IMAP_HOST"),
        "port": env.get("TRMS_IMAP_PORT"),
        "username": env.get("TRMS_IMAP_USERNAME"),
        "password": env.get("TRMS_IMAP_PASSWORD"),
        "mailbox": env.get("TRMS_IMAP_MAILBOX"),
        "poll_interval_seconds": env.get("TRMS_IMAP_POLL_INTERVAL_SECONDS"),
        "use_ssl": env.get("TRMS_IMAP_USE_SSL"),
        "starttls": env.get("TRMS_IMAP_STARTTLS"),
    }
    env_has_values = any(value is not None for value in env_values.values())
    if not explicit_has_values and not env_has_values:
        return None

    values = dict(env_values)
    for key, value in explicit.items():
        if value is not None:
            values[key] = value

    if not _has_meaningful_value(values.get("host")):
        issues.append("TRMS_IMAP_HOST is required when any TRMS_IMAP_* setting is configured")
    if not _has_meaningful_value(values.get("port")):
        issues.append("TRMS_IMAP_PORT is required when any TRMS_IMAP_* setting is configured")
    if not _has_meaningful_value(values.get("username")):
        issues.append("TRMS_IMAP_USERNAME is required when any TRMS_IMAP_* setting is configured")
    if not _has_meaningful_value(values.get("password")):
        issues.append("TRMS_IMAP_PASSWORD is required when any TRMS_IMAP_* setting is configured")

    return {
        "host": values.get("host"),
        "port": values.get("port"),
        "username": values.get("username"),
        "password": values.get("password"),
        "mailbox": values.get("mailbox") if values.get("mailbox") is not None else "INBOX",
        "poll_interval_seconds": (
            values.get("poll_interval_seconds")
            if values.get("poll_interval_seconds") is not None
            else 30.0
        ),
        "use_ssl": values.get("use_ssl") if values.get("use_ssl") is not None else True,
        "starttls": values.get("starttls") if values.get("starttls") is not None else False,
    }


def apply_system_ai_provider_overrides(
    runtime_config: RuntimeConfig,
    system_config: SystemAiProviderConfig | None,
) -> RuntimeConfig:
    if system_config is None:
        return runtime_config

    return runtime_config.model_copy(
        update={
            "text_llm_provider": _merge_provider_override(
                fallback_provider=runtime_config.text_llm_provider,
                override=system_config.text_llm,
            ),
            "vlm_provider": _merge_provider_override(
                fallback_provider=runtime_config.vlm_provider,
                override=system_config.vlm,
            ),
        }
    )


def _merge_provider_override(
    *,
    fallback_provider: LLMProviderConfig | None,
    override: SystemAiProviderOverride,
) -> LLMProviderConfig | None:
    has_override_values = any(
        (
            override.base_url is not None,
            override.model is not None,
            override.timeout_seconds is not None,
            override.max_retries is not None,
            override.api_key is not None,
        )
    )
    if not has_override_values:
        return fallback_provider

    merged_api_key = override.api_key or (
        fallback_provider.api_key if fallback_provider is not None else None
    )
    merged_model = override.model or (
        fallback_provider.model if fallback_provider is not None else None
    )
    if merged_api_key is None or merged_model is None:
        return None

    return LLMProviderConfig.model_validate(
        {
            "api_key": merged_api_key,
            "base_url": (
                override.base_url
                or (
                    fallback_provider.base_url
                    if fallback_provider is not None
                    else DEFAULT_LLM_BASE_URL
                )
            ),
            "model": merged_model,
            "timeout_seconds": (
                override.timeout_seconds
                if override.timeout_seconds is not None
                else (
                    fallback_provider.timeout_seconds
                    if fallback_provider is not None
                    else DEFAULT_LLM_TIMEOUT_SECONDS
                )
            ),
            "max_retries": (
                override.max_retries
                if override.max_retries is not None
                else (
                    fallback_provider.max_retries
                    if fallback_provider is not None
                    else DEFAULT_LLM_MAX_RETRIES
                )
            ),
        }
    )


def load_runtime_environment_variables(env: Mapping[str, str] | None = None) -> Mapping[str, str]:
    if env is not None:
        return env

    dotenv_path = Path(os.environ.get(DOTENV_PATH_ENVIRONMENT_KEY, DEFAULT_DOTENV_PATH))
    dotenv_values = _read_dotenv_file(dotenv_path)
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


def _normalize_timezone_name(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"{field_name} must be a valid IANA timezone name") from error
    return normalized


def _normalize_email_address(value: str, *, field_name: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if " " in normalized or "\t" in normalized or "\n" in normalized or "\r" in normalized:
        raise ValueError(f"{field_name} must not contain whitespace")
    local_part, separator, domain_part = normalized.partition("@")
    if separator != "@" or not local_part or not domain_part or "@" in domain_part:
        raise ValueError(f"{field_name} must be a valid email address")
    if "." not in domain_part:
        raise ValueError(f"{field_name} must be a valid email address")
    return normalized


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


def _build_default_public_web_base_url(*, public_api_base_url: str) -> str:
    normalized = public_api_base_url.rstrip("/")
    if normalized.endswith("/api"):
        return normalized[:-4] or normalized
    return normalized


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
