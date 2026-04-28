from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from trms_backend.domain.recognitions import RecognitionFailureDetail, RecognitionFailureStage
from trms_backend.runtime_config import RuntimeConfig


class RecognitionLlmCapabilityStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class RecognitionLlmCapability(BaseModel):
    status: RecognitionLlmCapabilityStatus
    failure: RecognitionFailureDetail | None = None
    base_url: str | None = None
    model: str | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None


def resolve_recognition_llm_capability(runtime_config: RuntimeConfig) -> RecognitionLlmCapability:
    provider = runtime_config.llm_provider
    if provider is None:
        return RecognitionLlmCapability(
            status=RecognitionLlmCapabilityStatus.DISABLED,
            failure=RecognitionFailureDetail(
                stage=RecognitionFailureStage.AI,
                reason="llm_provider_not_configured",
            ),
        )
    return RecognitionLlmCapability(
        status=RecognitionLlmCapabilityStatus.ENABLED,
        base_url=provider.base_url,
        model=provider.model,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
    )
