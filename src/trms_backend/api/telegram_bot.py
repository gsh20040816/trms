from typing import Annotated, Awaitable, Callable

from fastapi import APIRouter, Header, HTTPException, Request, status

from trms_backend.api.error_responses import ensure_request_id


def build_telegram_bot_router(
    processor: Callable[[dict, str], Awaitable[None]] | None,
    *,
    webhook_secret: str | None,
) -> APIRouter:
    router = APIRouter(tags=["telegram-bot"])

    @router.post("/api/telegram/bot/webhook")
    async def telegram_bot_webhook(
        request: Request,
        telegram_secret_token: Annotated[
            str | None,
            Header(alias="X-Telegram-Bot-Api-Secret-Token"),
        ] = None,
    ):
        if processor is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="telegram bot is not configured",
            )
        _ensure_valid_webhook_secret(
            configured_secret=webhook_secret,
            received_secret=telegram_secret_token,
        )
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="telegram webhook payload must be a JSON object",
            )
        await processor(payload, ensure_request_id(request))
        return {"status": "ok"}

    return router


def _ensure_valid_webhook_secret(
    *,
    configured_secret: str | None,
    received_secret: str | None,
) -> None:
    normalized_secret = (configured_secret or "").strip()
    if not normalized_secret:
        return
    if (received_secret or "").strip() != normalized_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid telegram webhook secret",
        )
