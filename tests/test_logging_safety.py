from pathlib import Path

from trms_backend.logging_safety import (
    REDACTED_LOG_PATH,
    REDACTED_LOG_VALUE,
    sanitize_log_fields,
)


def test_sanitize_log_fields_redacts_secret_keys_and_bearer_text():
    sanitized = sanitize_log_fields(
        {
            "telegram_bot_token": "123456:secret-token",
            "oauth_client_secret": "oauth-secret",
            "mail_password": "mail-secret",
            "message": "authorization=Bearer secret-token token=abc123",
        }
    )

    assert sanitized["telegram_bot_token"] == REDACTED_LOG_VALUE
    assert sanitized["oauth_client_secret"] == REDACTED_LOG_VALUE
    assert sanitized["mail_password"] == REDACTED_LOG_VALUE
    assert sanitized["message"] == "authorization=[redacted] token=[redacted]"


def test_sanitize_log_fields_redacts_local_paths_and_file_urls():
    sanitized = sanitize_log_fields(
        {
            "root_dir": Path("/srv/trms/materials"),
            "artifact_url": "https://storage.example.com/private/task-1/export.csv?signature=secret",
            "download_url": "s3://trms-prod/private/task-1/export.csv",
            "public_api_base_url": "https://api.example.com/v1",
        }
    )

    assert sanitized["root_dir"] == REDACTED_LOG_PATH
    assert sanitized["artifact_url"] == "https://storage.example.com/[redacted-path]"
    assert sanitized["download_url"] == "s3://trms-prod/[redacted-path]"
    assert sanitized["public_api_base_url"] == "https://api.example.com/v1"
