from alembic import command
from fastapi.testclient import TestClient

from trms_backend.infrastructure.database import build_alembic_config
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config


class FakeTelegramWebhookProcessor:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, str]] = []
        self.closed = False
        self.configured_webhooks: list[dict[str, object]] = []

    async def process_update(self, payload: dict, request_id: str) -> None:
        self.calls.append((payload, request_id))

    async def configure_webhook(
        self,
        *,
        webhook_url: str,
        secret_token: str | None = None,
        allowed_updates: list[str] | None = None,
    ) -> None:
        self.configured_webhooks.append(
            {
                "webhook_url": webhook_url,
                "secret_token": secret_token,
                "allowed_updates": allowed_updates,
            }
        )

    async def close(self) -> None:
        self.closed = True


def make_client(tmp_path, *, processor=None, env: dict[str, str] | None = None):
    runtime_env = {
        "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
        "TRMS_TELEGRAM_BOT_TOKEN": "telegram-bot-token",
        "TRMS_TELEGRAM_WEBHOOK_SECRET": "telegram-webhook-secret",
        "TRMS_PUBLIC_WEB_BASE_URL": "https://trms.example.edu",
    }
    if env is not None:
        runtime_env.update(env)
    runtime_config = load_runtime_config(env=runtime_env)
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            telegram_webhook_processor=processor,
        )
    )


def test_telegram_bot_webhook_requires_valid_secret(tmp_path):
    processor = FakeTelegramWebhookProcessor()
    client = make_client(tmp_path, processor=processor)

    response = client.post(
        "/api/telegram/bot/webhook",
        json={"update_id": 1},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid telegram webhook secret"
    assert processor.calls == []


def test_telegram_bot_webhook_forwards_payload_to_processor(tmp_path):
    processor = FakeTelegramWebhookProcessor()
    client = make_client(tmp_path, processor=processor)

    response = client.post(
        "/api/telegram/bot/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-webhook-secret"},
        json={"update_id": 1, "message": {"message_id": 10}},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert processor.calls[0][0]["update_id"] == 1


def test_production_startup_configures_telegram_webhook(tmp_path):
    processor = FakeTelegramWebhookProcessor()
    database_url = f"sqlite:///{tmp_path}/test.db"
    command.upgrade(build_alembic_config(database_url), "head")

    with make_client(
        tmp_path,
        processor=processor,
        env={
            "TRMS_ENV": "production",
            "DATABASE_URL": database_url,
            "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
            "TRMS_CORS_ALLOWED_ORIGINS": "https://trms.example.edu",
            "TRMS_STORAGE_BACKEND": "local",
            "MATERIAL_STORAGE_DIR": str(tmp_path / "materials"),
            "TRMS_API_HOST": "0.0.0.0",
            "TRMS_API_PORT": "9876",
        },
    ):
        pass

    assert processor.configured_webhooks == [
        {
            "webhook_url": "https://trms.example.edu/api/telegram/bot/webhook",
            "secret_token": "telegram-webhook-secret",
            "allowed_updates": ["message"],
        }
    ]


def test_non_production_startup_does_not_configure_telegram_webhook(tmp_path):
    processor = FakeTelegramWebhookProcessor()

    with make_client(
        tmp_path,
        processor=processor,
        env={
            "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
        },
    ):
        pass

    assert processor.configured_webhooks == []
