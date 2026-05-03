from fastapi.testclient import TestClient

from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config


class FakeTelegramWebhookProcessor:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, str]] = []
        self.closed = False

    async def process_update(self, payload: dict, request_id: str) -> None:
        self.calls.append((payload, request_id))

    async def close(self) -> None:
        self.closed = True


def make_client(tmp_path, *, processor=None):
    runtime_config = load_runtime_config(
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
            "TRMS_TELEGRAM_BOT_TOKEN": "telegram-bot-token",
            "TRMS_TELEGRAM_WEBHOOK_SECRET": "telegram-webhook-secret",
            "TRMS_PUBLIC_WEB_BASE_URL": "https://trms.example.edu",
        }
    )
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
