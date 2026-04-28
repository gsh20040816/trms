from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import trms_backend.runtime_config as runtime_config_module
from trms_backend.main import create_app
from trms_backend.runtime_config import (
    RuntimeConfigError,
    load_runtime_config,
    load_runtime_environment_variables,
)


def test_load_runtime_config_uses_development_defaults():
    config = load_runtime_config(env={})

    assert config.environment == "development"
    assert config.database_url == "sqlite:///./trms.db"
    assert config.file_storage.backend == "local"
    assert config.material_storage_dir == Path("data/materials")
    assert config.cors_allowed_origins == (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )
    assert config.public_api_base_url == "http://127.0.0.1:9876/api"
    assert config.api_host == "127.0.0.1"
    assert config.api_port == 9876
    assert config.async_jobs.mode == "in_process"
    assert config.async_jobs.worker_poll_interval_seconds == 5
    assert config.auth.allow_admin_self_register is True
    assert config.auth.bootstrap_admin_token is None
    assert config.auth.telegram_inbound_token is None
    assert config.llm_provider is None


def test_load_runtime_environment_variables_reads_root_dotenv_file(monkeypatch, tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "TRMS_API_HOST=0.0.0.0",
                "TRMS_API_PORT=8100",
                "TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:4173",
                "TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api",
                'TRMS_LLM_API_KEY="sk-dotenv-secret"',
                "TRMS_LLM_MODEL='gpt-4.1-mini'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(runtime_config_module, "DEFAULT_DOTENV_PATH", dotenv_path)
    monkeypatch.delenv("TRMS_API_HOST", raising=False)
    monkeypatch.delenv("TRMS_API_PORT", raising=False)
    monkeypatch.delenv("TRMS_CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("TRMS_PUBLIC_API_BASE_URL", raising=False)
    monkeypatch.delenv("TRMS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("TRMS_LLM_MODEL", raising=False)

    environment = load_runtime_environment_variables()
    config = load_runtime_config(env=environment)

    assert config.api_host == "0.0.0.0"
    assert config.api_port == 8100
    assert config.cors_allowed_origins == ("http://127.0.0.1:4173",)
    assert config.public_api_base_url == "http://127.0.0.1:8100/api"
    assert config.llm_provider is not None
    assert config.llm_provider.api_key.get_secret_value() == "sk-dotenv-secret"
    assert config.llm_provider.model == "gpt-4.1-mini"


def test_process_environment_overrides_root_dotenv(monkeypatch, tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("TRMS_API_PORT=8100\n", encoding="utf-8")

    monkeypatch.setattr(runtime_config_module, "DEFAULT_DOTENV_PATH", dotenv_path)
    monkeypatch.setenv("TRMS_API_PORT", "8200")

    config = load_runtime_config(env=load_runtime_environment_variables())

    assert config.api_port == 8200


def test_load_runtime_config_requires_explicit_production_settings():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(env={"TRMS_ENV": "production"})

    message = str(exc_info.value)
    assert "DATABASE_URL is required when TRMS_ENV=production" in message
    assert "TRMS_STORAGE_BACKEND is required when TRMS_ENV=production" in message
    assert "TRMS_CORS_ALLOWED_ORIGINS is required when TRMS_ENV=production" in message
    assert "TRMS_PUBLIC_API_BASE_URL is required when TRMS_ENV=production" in message
    assert "TRMS_API_HOST is required when TRMS_ENV=production" in message
    assert "TRMS_API_PORT is required when TRMS_ENV=production" in message


def test_load_runtime_config_rejects_illegal_port():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(env={"TRMS_API_PORT": "70000"})

    assert "api_port" in str(exc_info.value)


def test_load_runtime_config_defaults_to_worker_mode_in_production():
    config = load_runtime_config(
        env={
            "TRMS_ENV": "production",
            "DATABASE_URL": "sqlite:///./prod.db",
            "TRMS_STORAGE_BACKEND": "s3",
            "TRMS_STORAGE_S3_ENDPOINT": "https://minio.example.com",
            "TRMS_STORAGE_S3_BUCKET": "trms-prod",
            "TRMS_STORAGE_S3_ACCESS_KEY_ID": "prod-access",
            "TRMS_STORAGE_S3_SECRET_ACCESS_KEY": "prod-secret",
            "TRMS_CORS_ALLOWED_ORIGINS": "https://trms.example.edu",
            "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
            "TRMS_API_HOST": "0.0.0.0",
            "TRMS_API_PORT": "8000",
        }
    )

    assert config.environment == "production"
    assert config.async_jobs.mode == "worker"
    assert config.auth.allow_admin_self_register is False
    assert config.file_storage.backend == "s3"


def test_load_runtime_config_rejects_in_process_mode_in_production():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(
            env={
                "TRMS_ENV": "production",
                "DATABASE_URL": "sqlite:///./prod.db",
                "TRMS_STORAGE_BACKEND": "s3",
                "TRMS_STORAGE_S3_ENDPOINT": "https://minio.example.com",
                "TRMS_STORAGE_S3_BUCKET": "trms-prod",
                "TRMS_STORAGE_S3_ACCESS_KEY_ID": "prod-access",
                "TRMS_STORAGE_S3_SECRET_ACCESS_KEY": "prod-secret",
                "TRMS_CORS_ALLOWED_ORIGINS": "https://trms.example.edu",
                "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
                "TRMS_API_HOST": "0.0.0.0",
                "TRMS_API_PORT": "8000",
                "TRMS_ASYNC_JOB_MODE": "in_process",
            }
        )

    assert "TRMS_ASYNC_JOB_MODE=in_process is not allowed when TRMS_ENV=production" in str(
        exc_info.value
    )


def test_load_runtime_config_rejects_local_storage_in_production():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(
            env={
                "TRMS_ENV": "production",
                "DATABASE_URL": "sqlite:///./prod.db",
                "TRMS_STORAGE_BACKEND": "local",
                "MATERIAL_STORAGE_DIR": "./prod-materials",
                "TRMS_CORS_ALLOWED_ORIGINS": "https://trms.example.edu",
                "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
                "TRMS_API_HOST": "0.0.0.0",
                "TRMS_API_PORT": "8000",
            }
        )

    assert "TRMS_STORAGE_BACKEND=local is not allowed when TRMS_ENV=production" in str(
        exc_info.value
    )


def test_load_runtime_config_rejects_invalid_async_job_mode():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(env={"TRMS_ASYNC_JOB_MODE": "sidecar"})

    assert "async_jobs.mode" in str(exc_info.value)


def test_load_runtime_config_reads_llm_provider_and_normalizes_base_url():
    config = load_runtime_config(
        env={
            "TRMS_LLM_API_KEY": " sk-test-secret ",
            "TRMS_LLM_BASE_URL": " https://llm.example.com/v1/ ",
            "TRMS_LLM_MODEL": " gpt-4.1-mini ",
            "TRMS_LLM_TIMEOUT_SECONDS": "45",
            "TRMS_LLM_MAX_RETRIES": "3",
        }
    )

    assert config.llm_provider is not None
    assert config.llm_provider.api_key.get_secret_value() == "sk-test-secret"
    assert config.llm_provider.base_url == "https://llm.example.com/v1"
    assert config.llm_provider.model == "gpt-4.1-mini"
    assert config.llm_provider.timeout_seconds == 45
    assert config.llm_provider.max_retries == 3


def test_load_runtime_config_requires_llm_api_key_when_other_llm_settings_present():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(
            env={
                "TRMS_LLM_MODEL": "gpt-4.1-mini",
                "TRMS_LLM_BASE_URL": "https://llm.example.com/v1",
            }
        )

    assert "TRMS_LLM_API_KEY is required when any TRMS_LLM_* setting is configured" in str(
        exc_info.value
    )


def test_llm_provider_safe_log_fields_redact_api_key():
    config = load_runtime_config(
        env={
            "TRMS_LLM_API_KEY": "sk-live-secret-value",
            "TRMS_LLM_MODEL": "gpt-4.1-mini",
        }
    )

    assert config.llm_provider is not None
    safe_log_fields = config.llm_provider.to_safe_log_fields()

    assert safe_log_fields["api_key"] == "[redacted]"
    assert safe_log_fields["api_key_configured"] is True
    assert "sk-live-secret-value" not in str(safe_log_fields)


def test_auth_config_reads_bootstrap_token_and_redacts_it_from_logs():
    config = load_runtime_config(
        env={
            "TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER": "false",
            "TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN": " bootstrap-secret ",
            "TRMS_AUTH_TELEGRAM_INBOUND_TOKEN": " telegram-inbound-secret ",
        }
    )

    assert config.auth.allow_admin_self_register is False
    assert config.auth.bootstrap_admin_token is not None
    assert config.auth.bootstrap_admin_token.get_secret_value() == "bootstrap-secret"
    assert config.auth.telegram_inbound_token is not None
    assert config.auth.telegram_inbound_token.get_secret_value() == "telegram-inbound-secret"

    safe_log_fields = config.auth.to_safe_log_fields()

    assert safe_log_fields["bootstrap_admin_token"] == "[redacted]"
    assert safe_log_fields["bootstrap_admin_token_configured"] is True
    assert safe_log_fields["telegram_inbound_token"] == "[redacted]"
    assert safe_log_fields["telegram_inbound_token_configured"] is True
    assert "bootstrap-secret" not in str(safe_log_fields)
    assert "telegram-inbound-secret" not in str(safe_log_fields)


def test_s3_file_storage_safe_log_fields_redact_credentials():
    config = load_runtime_config(
        env={
            "TRMS_STORAGE_BACKEND": "s3",
            "TRMS_STORAGE_S3_ENDPOINT": "https://minio.example.com",
            "TRMS_STORAGE_S3_BUCKET": "trms-prod",
            "TRMS_STORAGE_S3_ACCESS_KEY_ID": "access-secret",
            "TRMS_STORAGE_S3_SECRET_ACCESS_KEY": "secret-secret",
        }
    )

    safe_log_fields = config.file_storage.to_safe_log_fields()

    assert safe_log_fields["backend"] == "s3"
    assert safe_log_fields["access_key_id"] == "[redacted]"
    assert safe_log_fields["secret_access_key"] == "[redacted]"
    assert "access-secret" not in str(safe_log_fields)
    assert "secret-secret" not in str(safe_log_fields)


def test_local_file_storage_safe_log_fields_redact_root_dir():
    config = load_runtime_config(
        env={},
        material_storage_dir="/srv/trms/materials",
    )

    safe_log_fields = config.file_storage.to_safe_log_fields()

    assert safe_log_fields["backend"] == "local"
    assert safe_log_fields["root_dir"] == "[redacted-path]"
    assert "/srv/trms/materials" not in str(safe_log_fields)


def test_runtime_config_safe_log_fields_redact_nested_secrets_and_paths():
    config = load_runtime_config(
        env={
            "TRMS_LLM_API_KEY": "sk-live-secret-value",
            "TRMS_LLM_MODEL": "gpt-4.1-mini",
            "TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN": "bootstrap-secret",
        },
        material_storage_dir="/srv/trms/materials",
    )

    safe_log_fields = config.to_safe_log_fields()

    assert safe_log_fields["file_storage"]["root_dir"] == "[redacted-path]"
    assert safe_log_fields["auth"]["bootstrap_admin_token"] == "[redacted]"
    assert safe_log_fields["llm_provider"]["api_key"] == "[redacted]"
    assert "bootstrap-secret" not in str(safe_log_fields)
    assert "sk-live-secret-value" not in str(safe_log_fields)
    assert "/srv/trms/materials" not in str(safe_log_fields)


def test_create_app_applies_configured_cors_origins(tmp_path):
    config = load_runtime_config(
        env={},
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "materials",
        cors_allowed_origins="http://example.com",
        public_api_base_url="http://example.com/api",
    )
    client = TestClient(create_app(runtime_config=config))

    response = client.options(
        "/api/tasks",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://example.com"
