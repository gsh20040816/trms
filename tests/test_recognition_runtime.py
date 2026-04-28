from trms_backend.application.recognition_runtime import (
    RecognitionLlmCapabilityStatus,
    resolve_recognition_llm_capability,
)
from trms_backend.runtime_config import load_runtime_config


def test_resolve_recognition_llm_capability_returns_disabled_when_provider_missing():
    config = load_runtime_config(env={})

    capability = resolve_recognition_llm_capability(config)

    assert capability.status == RecognitionLlmCapabilityStatus.DISABLED
    assert capability.failure is not None
    assert capability.failure.stage == "ai"
    assert capability.failure.reason == "llm_provider_not_configured"


def test_resolve_recognition_llm_capability_returns_enabled_provider_settings():
    config = load_runtime_config(
        env={
            "TRMS_LLM_API_KEY": "sk-test-secret",
            "TRMS_LLM_MODEL": "gpt-4.1-mini",
            "TRMS_LLM_TIMEOUT_SECONDS": "12.5",
            "TRMS_LLM_MAX_RETRIES": "4",
        }
    )

    capability = resolve_recognition_llm_capability(config)

    assert capability.status == RecognitionLlmCapabilityStatus.ENABLED
    assert capability.failure is None
    assert capability.base_url == "https://api.openai.com/v1"
    assert capability.model == "gpt-4.1-mini"
    assert capability.timeout_seconds == 12.5
    assert capability.max_retries == 4
