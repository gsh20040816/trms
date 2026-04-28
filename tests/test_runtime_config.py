from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trms_backend.main import create_app
from trms_backend.runtime_config import RuntimeConfigError, load_runtime_config


def test_load_runtime_config_uses_development_defaults():
    config = load_runtime_config(env={})

    assert config.environment == "development"
    assert config.database_url == "sqlite:///./trms.db"
    assert config.material_storage_dir == Path("data/materials")
    assert config.cors_allowed_origins == (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )
    assert config.public_api_base_url == "http://127.0.0.1:8000/api"
    assert config.api_host == "127.0.0.1"
    assert config.api_port == 8000


def test_load_runtime_config_requires_explicit_production_settings():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(env={"TRMS_ENV": "production"})

    message = str(exc_info.value)
    assert "DATABASE_URL is required when TRMS_ENV=production" in message
    assert "MATERIAL_STORAGE_DIR is required when TRMS_ENV=production" in message
    assert "TRMS_CORS_ALLOWED_ORIGINS is required when TRMS_ENV=production" in message
    assert "TRMS_PUBLIC_API_BASE_URL is required when TRMS_ENV=production" in message
    assert "TRMS_API_HOST is required when TRMS_ENV=production" in message
    assert "TRMS_API_PORT is required when TRMS_ENV=production" in message


def test_load_runtime_config_rejects_illegal_port():
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(env={"TRMS_API_PORT": "70000"})

    assert "api_port" in str(exc_info.value)


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
