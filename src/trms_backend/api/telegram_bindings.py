from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from trms_backend.domain.telegram_bindings import (
    TelegramAccountBindingConflictError,
    TelegramAccountBindingRepository,
    TelegramAccountBindingUpsert,
    TelegramSubmissionIdentityResolver,
)


class TelegramAccountBindingRequest(BaseModel):
    member_id: str = Field(min_length=1)
    telegram_username: str | None = Field(default=None, max_length=64)


def build_telegram_binding_router(
    binding_repository: TelegramAccountBindingRepository,
) -> APIRouter:
    router = APIRouter(tags=["telegram-bindings"])
    submission_identity_resolver = TelegramSubmissionIdentityResolver(binding_repository)

    @router.put("/api/telegram-bindings/{telegram_user_id}")
    def upsert_telegram_account_binding(
        telegram_user_id: int,
        payload: TelegramAccountBindingRequest,
    ):
        try:
            binding = binding_repository.upsert(
                TelegramAccountBindingUpsert(
                    telegram_user_id=telegram_user_id,
                    member_id=payload.member_id,
                    telegram_username=payload.telegram_username,
                )
            )
        except TelegramAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {"item": binding}

    @router.get("/api/telegram-bindings/{telegram_user_id}")
    def get_telegram_account_binding(telegram_user_id: int):
        binding = binding_repository.get_by_telegram_user_id(telegram_user_id)
        if binding is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="telegram account binding not found",
            )
        return {"item": binding}

    @router.get("/api/telegram-bindings/{telegram_user_id}/submission-identity")
    def resolve_telegram_submission_identity(telegram_user_id: int):
        return {"item": submission_identity_resolver.resolve(telegram_user_id)}

    return router
