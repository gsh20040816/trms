from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, SecretStr, field_validator


class SystemAiProviderOverride(BaseModel):
    base_url: str | None = None
    model: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=300)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    api_key: SecretStr | None = None

    @field_validator("base_url", "model", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_optional_api_key(cls, value: SecretStr | str | None) -> SecretStr | None:
        if value is None:
            return None
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        normalized = raw_value.strip()
        if not normalized:
            return None
        return SecretStr(normalized)


class SystemAiProviderConfig(BaseModel):
    text_llm: SystemAiProviderOverride = Field(default_factory=SystemAiProviderOverride)
    vlm: SystemAiProviderOverride = Field(default_factory=SystemAiProviderOverride)


class SystemAiProviderConfigSummary(BaseModel):
    base_url: str | None = None
    model: str | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None
    api_key_configured: bool = False


class SystemAiProviderConfigPatch(BaseModel):
    text_llm: SystemAiProviderOverride = Field(default_factory=SystemAiProviderOverride)
    vlm: SystemAiProviderOverride = Field(default_factory=SystemAiProviderOverride)


class SystemAiProviderConfigRepository(Protocol):
    def get(self) -> SystemAiProviderConfig | None:
        raise NotImplementedError

    def patch(self, payload: SystemAiProviderConfigPatch) -> SystemAiProviderConfig:
        raise NotImplementedError


def summarize_system_ai_provider_override(
    override: SystemAiProviderOverride,
) -> SystemAiProviderConfigSummary:
    return SystemAiProviderConfigSummary(
        base_url=override.base_url,
        model=override.model,
        timeout_seconds=override.timeout_seconds,
        max_retries=override.max_retries,
        api_key_configured=override.api_key is not None,
    )
